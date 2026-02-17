"""Comprehensive tests for pbx/features/mfa.py"""

import base64
import hashlib
import hmac
import secrets
import sqlite3
import struct
import time
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# TOTPGenerator tests
# ---------------------------------------------------------------------------
class TestTOTPGenerator:
    """Tests for the TOTPGenerator class."""

    @pytest.mark.unit
    def test_init_defaults(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator()
            assert len(t.secret) == 20
            assert t.period == 30
            assert t.digits == 6

    @pytest.mark.unit
    def test_init_custom_secret(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            secret = b"0123456789abcdef0123"
            t = TOTPGenerator(secret=secret, period=60, digits=8)
            assert t.secret == secret
            assert t.period == 60
            assert t.digits == 8

    @pytest.mark.unit
    def test_generate_returns_string_of_correct_length(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20, digits=6)
            code = t.generate(timestamp=1000000)
            assert isinstance(code, str)
            assert len(code) == 6

    @pytest.mark.unit
    def test_generate_eight_digits(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20, digits=8)
            code = t.generate(timestamp=1000000)
            assert len(code) == 8

    @pytest.mark.unit
    def test_generate_uses_current_time_when_none(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            code = t.generate()
            assert isinstance(code, str)
            assert len(code) == 6

    @pytest.mark.unit
    def test_generate_deterministic(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            c1 = t.generate(timestamp=1000000)
            c2 = t.generate(timestamp=1000000)
            assert c1 == c2

    @pytest.mark.unit
    def test_generate_different_timestamps_differ(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20, period=30)
            c1 = t.generate(timestamp=0)
            c2 = t.generate(timestamp=90)
            assert c1 != c2

    @pytest.mark.unit
    def test_verify_correct_code(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            ts = 1000000
            code = t.generate(timestamp=ts)
            assert t.verify(code, timestamp=ts) is True

    @pytest.mark.unit
    def test_verify_wrong_code(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            assert t.verify("000000", timestamp=1000000) is False

    @pytest.mark.unit
    def test_verify_window(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20, period=30)
            ts = 1000000
            code_prev = t.generate(timestamp=ts - 30)
            assert t.verify(code_prev, timestamp=ts, window=1) is True

    @pytest.mark.unit
    def test_verify_outside_window(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20, period=30)
            ts = 1000000
            code_far = t.generate(timestamp=ts - 90)
            assert t.verify(code_far, timestamp=ts, window=1) is False

    @pytest.mark.unit
    def test_verify_uses_current_time_when_none(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            code = t.generate()
            assert t.verify(code) is True

    @pytest.mark.unit
    def test_hotp_produces_padded_code(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20, digits=6)
            code = t._hotp(0)
            assert len(code) == 6
            assert code.isdigit()

    @pytest.mark.unit
    def test_constant_time_compare_equal(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            assert t._constant_time_compare("abc", "abc") is True

    @pytest.mark.unit
    def test_constant_time_compare_different(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            assert t._constant_time_compare("abc", "abd") is False

    @pytest.mark.unit
    def test_constant_time_compare_different_length(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            assert t._constant_time_compare("ab", "abc") is False

    @pytest.mark.unit
    def test_get_provisioning_uri(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20, period=30, digits=6)
            uri = t.get_provisioning_uri("1001", issuer="TestPBX")
            assert uri.startswith("otpauth://totp/TestPBX:1001?")
            assert "secret=" in uri
            assert "issuer=TestPBX" in uri
            assert "period=30" in uri
            assert "digits=6" in uri
            assert "algorithm=SHA1" in uri

    @pytest.mark.unit
    def test_get_provisioning_uri_default_issuer(self) -> None:
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            t = TOTPGenerator(secret=b"A" * 20)
            uri = t.get_provisioning_uri("ext100")
            assert "Warden Voip" in uri


# ---------------------------------------------------------------------------
# YubiKeyOTPVerifier tests
# ---------------------------------------------------------------------------
class TestYubiKeyOTPVerifier:
    """Tests for YubiKeyOTPVerifier."""

    def _make_verifier(self, client_id: str | None = None, api_key: str | None = None):
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import YubiKeyOTPVerifier

            return YubiKeyOTPVerifier(client_id=client_id, api_key=api_key)

    @pytest.mark.unit
    def test_init_defaults(self) -> None:
        v = self._make_verifier()
        assert v.client_id == "1"
        assert v.api_key is None

    @pytest.mark.unit
    def test_init_custom(self) -> None:
        v = self._make_verifier(client_id="42", api_key="c2VjcmV0")
        assert v.client_id == "42"
        assert v.api_key == "c2VjcmV0"

    @pytest.mark.unit
    def test_verify_otp_too_short(self) -> None:
        v = self._make_verifier()
        ok, err = v.verify_otp("short")
        assert ok is False
        assert "44 characters" in err

    @pytest.mark.unit
    def test_verify_otp_empty(self) -> None:
        v = self._make_verifier()
        ok, _err = v.verify_otp("")
        assert ok is False

    @pytest.mark.unit
    def test_verify_otp_none(self) -> None:
        v = self._make_verifier()
        ok, _err = v.verify_otp(None)
        assert ok is False

    @pytest.mark.unit
    def test_verify_otp_invalid_chars(self) -> None:
        v = self._make_verifier()
        bad_otp = "a" * 44  # 'a' is not in modhex charset
        ok, err = v.verify_otp(bad_otp)
        assert ok is False
        assert "invalid characters" in err

    @pytest.mark.unit
    def test_verify_otp_valid_format_calls_yubico(self) -> None:
        v = self._make_verifier()
        # 44 modhex characters
        otp = "c" * 44
        with patch.object(v, "_verify_via_yubico", return_value=(True, None)) as mock_yubi:
            ok, err = v.verify_otp(otp)
            assert ok is True
            assert err is None
            mock_yubi.assert_called_once_with(otp)

    @pytest.mark.unit
    def test_extract_public_id(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        assert v.extract_public_id(otp) == "c" * 12

    @pytest.mark.unit
    def test_extract_public_id_short(self) -> None:
        v = self._make_verifier()
        assert v.extract_public_id("abc") is None

    @pytest.mark.unit
    def test_extract_public_id_none(self) -> None:
        v = self._make_verifier()
        assert v.extract_public_id(None) is None

    @pytest.mark.unit
    def test_extract_public_id_empty(self) -> None:
        v = self._make_verifier()
        assert v.extract_public_id("") is None

    @pytest.mark.unit
    def test_build_yubico_params_without_api_key(self) -> None:
        v = self._make_verifier(client_id="99")
        params = v._build_yubico_params("otp_val", "nonce_val")
        assert params["id"] == "99"
        assert params["otp"] == "otp_val"
        assert params["nonce"] == "nonce_val"
        assert "h" not in params

    @pytest.mark.unit
    def test_build_yubico_params_with_api_key(self) -> None:
        api_key = base64.b64encode(b"secretkey1234567").decode("utf-8")
        v = self._make_verifier(client_id="99", api_key=api_key)
        params = v._build_yubico_params("otp_val", "nonce_val")
        assert "h" in params

    @pytest.mark.unit
    def test_verify_yubico_response_signature_nonce_mismatch(self) -> None:
        v = self._make_verifier()
        resp = {"nonce": "wrong_nonce", "status": "OK"}
        assert v._verify_yubico_response_signature(resp, "correct_nonce") is False

    @pytest.mark.unit
    def test_verify_yubico_response_signature_nonce_match_no_key(self) -> None:
        v = self._make_verifier()
        resp = {"nonce": "correct", "status": "OK"}
        assert v._verify_yubico_response_signature(resp, "correct") is True

    @pytest.mark.unit
    def test_verify_yubico_response_signature_hmac_mismatch(self) -> None:
        api_key = base64.b64encode(b"secretkey1234567").decode("utf-8")
        v = self._make_verifier(api_key=api_key)
        resp = {"nonce": "correct", "status": "OK", "h": "bad_signature"}
        assert v._verify_yubico_response_signature(resp, "correct") is False

    @pytest.mark.unit
    def test_verify_yubico_response_signature_hmac_match(self) -> None:
        api_key_bytes = b"secretkey1234567"
        api_key = base64.b64encode(api_key_bytes).decode("utf-8")
        v = self._make_verifier(api_key=api_key)
        # Build the expected response dict (without h)
        resp_data = {"nonce": "mynonce", "status": "OK"}
        sorted_items = sorted(resp_data.items())
        param_string = "&".join(f"{k}={v_}" for k, v_ in sorted_items)
        sig = hmac.new(api_key_bytes, param_string.encode("utf-8"), hashlib.sha1)
        sig_b64 = base64.b64encode(sig.digest()).decode("utf-8")
        resp_data["h"] = sig_b64
        assert v._verify_yubico_response_signature(resp_data, "mynonce") is True

    @pytest.mark.unit
    def test_query_yubico_server_success(self) -> None:
        v = self._make_verifier()
        response_text = "status=OK\notp=myotp\nnonce=mynonce\n"
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_text.encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = v._query_yubico_server("https://api.yubico.com/wsapi/2.0/verify", {"id": "1"})
        assert result is not None
        assert result["status"] == "OK"
        assert result["otp"] == "myotp"

    @pytest.mark.unit
    def test_query_yubico_server_network_error(self) -> None:
        v = self._make_verifier()
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = v._query_yubico_server("https://api.yubico.com/wsapi/2.0/verify", {"id": "1"})
        assert result is None

    @pytest.mark.unit
    def test_verify_via_yubico_ok(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v, "_query_yubico_server", return_value={"status": "OK", "otp": otp, "nonce": "x"}
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is True
        assert err is None

    @pytest.mark.unit
    def test_verify_via_yubico_replayed(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v,
                "_query_yubico_server",
                return_value={"status": "REPLAYED_OTP", "nonce": "x"},
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "replay" in err.lower()

    @pytest.mark.unit
    def test_verify_via_yubico_bad_otp(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v,
                "_query_yubico_server",
                return_value={"status": "BAD_OTP", "nonce": "x"},
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "Invalid OTP" in err

    @pytest.mark.unit
    def test_verify_via_yubico_no_such_client(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v,
                "_query_yubico_server",
                return_value={"status": "NO_SUCH_CLIENT", "nonce": "x"},
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "client" in err.lower()

    @pytest.mark.unit
    def test_verify_via_yubico_bad_signature(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v,
                "_query_yubico_server",
                return_value={"status": "BAD_SIGNATURE", "nonce": "x"},
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "signature" in err.lower()

    @pytest.mark.unit
    def test_verify_via_yubico_missing_parameter(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v,
                "_query_yubico_server",
                return_value={"status": "MISSING_PARAMETER", "nonce": "x"},
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "parameter" in err.lower()

    @pytest.mark.unit
    def test_verify_via_yubico_operation_not_allowed(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v,
                "_query_yubico_server",
                return_value={"status": "OPERATION_NOT_ALLOWED", "nonce": "x"},
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "not allowed" in err.lower()

    @pytest.mark.unit
    def test_verify_via_yubico_otp_mismatch(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v,
                "_query_yubico_server",
                return_value={"status": "OK", "otp": "d" * 44, "nonce": "x"},
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "mismatch" in err.lower()

    @pytest.mark.unit
    def test_verify_via_yubico_all_servers_fail(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with patch.object(v, "_query_yubico_server", return_value=None):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "unavailable" in err.lower()

    @pytest.mark.unit
    def test_verify_via_yubico_backend_error_then_none(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        responses = [
            {"status": "BACKEND_ERROR", "nonce": "x"},
            None,
            None,
            None,
            None,
        ]
        with (
            patch.object(v, "_query_yubico_server", side_effect=responses),
            patch.object(v, "_verify_yubico_response_signature", return_value=True),
        ):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "Backend error" in err

    @pytest.mark.unit
    def test_verify_via_yubico_exception(self) -> None:
        v = self._make_verifier()
        otp = "c" * 44
        with patch.object(v, "_build_yubico_params", side_effect=ValueError("boom")):
            ok, err = v._verify_via_yubico(otp)
        assert ok is False
        assert "boom" in err

    @pytest.mark.unit
    def test_verify_via_yubico_sig_fail_tries_next(self) -> None:
        """When signature verification fails, move to next server."""
        v = self._make_verifier()
        otp = "c" * 44
        with (
            patch.object(
                v,
                "_query_yubico_server",
                return_value={"status": "OK", "otp": otp, "nonce": "x"},
            ),
            patch.object(v, "_verify_yubico_response_signature", return_value=False),
        ):
            ok, _err = v._verify_via_yubico(otp)
        assert ok is False


# ---------------------------------------------------------------------------
# FIDO2Verifier tests
# ---------------------------------------------------------------------------
class TestFIDO2Verifier:
    """Tests for the FIDO2Verifier class."""

    def _make_verifier(self, fido2_available: bool = False):
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import FIDO2Verifier

            if fido2_available:
                with patch.dict(
                    "sys.modules",
                    {
                        "fido2": MagicMock(),
                        "fido2.server": MagicMock(),
                        "fido2.webauthn": MagicMock(),
                    },
                ):
                    v = FIDO2Verifier(rp_id="test.local", rp_name="Test")
                    v.fido2_available = True
                    return v
            else:
                v = FIDO2Verifier.__new__(FIDO2Verifier)
                v.logger = MagicMock()
                v.rp_id = "test.local"
                v.rp_name = "Test"
                v.fido2_available = False
                return v

    @pytest.mark.unit
    def test_init_without_fido2_lib(self) -> None:
        v = self._make_verifier(fido2_available=False)
        assert v.fido2_available is False
        assert v.rp_id == "test.local"

    @pytest.mark.unit
    def test_create_challenge(self) -> None:
        v = self._make_verifier()
        challenge = v.create_challenge()
        assert isinstance(challenge, str)
        assert len(challenge) > 0
        # Should be URL-safe base64 without padding
        assert "=" not in challenge

    @pytest.mark.unit
    def test_register_credential_missing_id(self) -> None:
        v = self._make_verifier()
        ok, err = v.register_credential("1001", {"public_key": "pk"})
        assert ok is False
        assert "Missing" in err

    @pytest.mark.unit
    def test_register_credential_missing_public_key(self) -> None:
        v = self._make_verifier()
        ok, err = v.register_credential("1001", {"credential_id": "cid"})
        assert ok is False
        assert "Missing" in err

    @pytest.mark.unit
    def test_register_credential_basic_mode(self) -> None:
        v = self._make_verifier(fido2_available=False)
        ok, cid = v.register_credential(
            "1001",
            {
                "credential_id": "my_cred",
                "public_key": "my_pk",
            },
        )
        assert ok is True
        assert cid == "my_cred"

    @pytest.mark.unit
    def test_register_credential_fido2_mode_valid(self) -> None:
        v = self._make_verifier(fido2_available=True)
        cred_id_b64 = base64.b64encode(b"x" * 32).decode("utf-8")
        ok, cid = v.register_credential(
            "1001",
            {
                "credential_id": cred_id_b64,
                "public_key": "pk",
            },
        )
        assert ok is True
        assert cid == cred_id_b64

    @pytest.mark.unit
    def test_register_credential_fido2_too_short(self) -> None:
        v = self._make_verifier(fido2_available=True)
        cred_id_b64 = base64.b64encode(b"x" * 5).decode("utf-8")
        ok, err = v.register_credential(
            "1001",
            {
                "credential_id": cred_id_b64,
                "public_key": "pk",
            },
        )
        assert ok is False
        assert "length" in err.lower()

    @pytest.mark.unit
    def test_register_credential_fido2_too_long(self) -> None:
        v = self._make_verifier(fido2_available=True)
        cred_id_b64 = base64.b64encode(b"x" * 2000).decode("utf-8")
        ok, err = v.register_credential(
            "1001",
            {
                "credential_id": cred_id_b64,
                "public_key": "pk",
            },
        )
        assert ok is False
        assert "length" in err.lower()

    @pytest.mark.unit
    def test_register_credential_fido2_bytes_credential_id(self) -> None:
        v = self._make_verifier(fido2_available=True)
        ok, _cid = v.register_credential(
            "1001",
            {
                "credential_id": b"x" * 32,
                "public_key": "pk",
            },
        )
        assert ok is True

    @pytest.mark.unit
    def test_verify_assertion_missing_data(self) -> None:
        v = self._make_verifier()
        ok, err = v.verify_assertion("cred", {}, b"pk")
        assert ok is False
        assert "Missing" in err

    @pytest.mark.unit
    def test_verify_assertion_missing_signature(self) -> None:
        v = self._make_verifier()
        ok, err = v.verify_assertion(
            "cred",
            {
                "authenticator_data": "ad",
                "client_data_json": "cdj",
            },
            b"pk",
        )
        assert ok is False
        assert "Missing" in err

    @pytest.mark.unit
    def test_verify_assertion_basic_mode_valid(self) -> None:
        v = self._make_verifier(fido2_available=False)
        auth_data = base64.b64encode(b"x" * 50).decode("utf-8")
        sig = base64.b64encode(b"y" * 70).decode("utf-8")
        cdj = base64.b64encode(b'{"type":"webauthn.get"}').decode("utf-8")
        ok, err = v.verify_assertion(
            "cred",
            {
                "authenticator_data": auth_data,
                "signature": sig,
                "client_data_json": cdj,
            },
            b"pk",
        )
        assert ok is True
        assert err is None

    @pytest.mark.unit
    def test_verify_assertion_basic_mode_short_auth_data(self) -> None:
        v = self._make_verifier(fido2_available=False)
        auth_data = base64.b64encode(b"x" * 10).decode("utf-8")
        sig = base64.b64encode(b"y" * 70).decode("utf-8")
        cdj = base64.b64encode(b'{"type":"webauthn.get"}').decode("utf-8")
        ok, err = v.verify_assertion(
            "cred",
            {
                "authenticator_data": auth_data,
                "signature": sig,
                "client_data_json": cdj,
            },
            b"pk",
        )
        assert ok is False
        assert "authenticator_data" in err.lower()

    @pytest.mark.unit
    def test_verify_assertion_basic_mode_short_sig(self) -> None:
        v = self._make_verifier(fido2_available=False)
        auth_data = base64.b64encode(b"x" * 50).decode("utf-8")
        sig = base64.b64encode(b"y" * 10).decode("utf-8")
        cdj = base64.b64encode(b'{"type":"webauthn.get"}').decode("utf-8")
        ok, err = v.verify_assertion(
            "cred",
            {
                "authenticator_data": auth_data,
                "signature": sig,
                "client_data_json": cdj,
            },
            b"pk",
        )
        assert ok is False
        assert "signature" in err.lower()

    @pytest.mark.unit
    def test_verify_assertion_decode_error(self) -> None:
        v = self._make_verifier(fido2_available=False)
        ok, err = v.verify_assertion(
            "cred",
            {
                "authenticator_data": "!!!invalid_base64!!!",
                "signature": "!!!invalid_base64!!!",
                "client_data_json": "!!!invalid_base64!!!",
            },
            b"pk",
        )
        assert ok is False
        assert "decode" in err.lower() or "Failed" in err

    @pytest.mark.unit
    def test_verify_assertion_string_public_key(self) -> None:
        v = self._make_verifier(fido2_available=False)
        auth_data = base64.b64encode(b"x" * 50).decode("utf-8")
        sig = base64.b64encode(b"y" * 70).decode("utf-8")
        cdj = base64.b64encode(b'{"type":"webauthn.get"}').decode("utf-8")
        pk = base64.b64encode(b"publickey").decode("utf-8")
        ok, _err = v.verify_assertion(
            "cred",
            {
                "authenticator_data": auth_data,
                "signature": sig,
                "client_data_json": cdj,
            },
            pk,
        )
        assert ok is True

    @pytest.mark.unit
    def test_verify_assertion_client_data_json_plain_string(self) -> None:
        """When client_data_json can't decode as b64, it should be treated as UTF-8 string."""
        v = self._make_verifier(fido2_available=False)
        auth_data = base64.b64encode(b"x" * 50).decode("utf-8")
        sig = base64.b64encode(b"y" * 70).decode("utf-8")
        # A string that is valid base64 but we just pass a json string directly as bytes
        cdj_bytes = b'{"type":"webauthn.get"}'
        ok, _err = v.verify_assertion(
            "cred",
            {
                "authenticator_data": auth_data,
                "signature": sig,
                "client_data_json": cdj_bytes,
            },
            b"pk",
        )
        assert ok is True


# ---------------------------------------------------------------------------
# MFAManager tests
# ---------------------------------------------------------------------------
class TestMFAManagerInit:
    """Tests for MFAManager initialization."""

    def _make_manager(self, config=None, database=None):
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager

            return MFAManager(database=database, config=config or {})

    @pytest.mark.unit
    def test_init_defaults(self) -> None:
        m = self._make_manager()
        assert m.enabled is True
        assert m.required is False
        assert m.backup_codes_count == 10
        assert m.yubikey_verifier is None
        assert m.fido2_verifier is None

    @pytest.mark.unit
    def test_init_disabled(self) -> None:
        m = self._make_manager(config={"security.mfa.enabled": False})
        assert m.enabled is False

    @pytest.mark.unit
    def test_init_yubikey_enabled(self) -> None:
        config = {
            "security.mfa.yubikey.enabled": True,
            "security.mfa.yubikey.client_id": "42",
            "security.mfa.yubikey.api_key": "key",
        }
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager

            m = MFAManager(config=config)
        assert m.yubikey_enabled is True
        assert m.yubikey_verifier is not None

    @pytest.mark.unit
    def test_init_fido2_enabled(self) -> None:
        config = {"security.mfa.fido2.enabled": True}
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager

            m = MFAManager(config=config)
        assert m.fido2_enabled is True
        assert m.fido2_verifier is not None

    @pytest.mark.unit
    def test_init_with_database(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        _m = self._make_manager(database=db)
        assert db.execute.call_count == 4  # 4 CREATE TABLE calls

    @pytest.mark.unit
    def test_init_schema_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.execute.side_effect = sqlite3.Error("fail")
        _m = self._make_manager(database=db)
        # Should not raise

    @pytest.mark.unit
    def test_init_postgresql_schema(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        _m = self._make_manager(database=db)
        assert db.execute.call_count == 4


class TestMFAManagerEnrollUser:
    """Tests for MFAManager.enroll_user."""

    def _make_manager(self, db=None, enabled=True):
        config = {"security.mfa.enabled": enabled}
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            enc = MagicMock()
            enc.derive_key.return_value = (b"k" * 32, b"salt" * 8)
            enc.encrypt_data.return_value = ("enc_data", "nonce_val", "tag_val")
            enc.hash_password.return_value = ("hashed", "salt_b64")
            mock_enc.return_value = enc
            from pbx.features.mfa import MFAManager

            m = MFAManager(database=db, config=config)
        return m

    @pytest.mark.unit
    def test_enroll_disabled(self) -> None:
        m = self._make_manager(enabled=False)
        ok, uri, codes = m.enroll_user("1001")
        assert ok is False
        assert uri is None
        assert codes is None

    @pytest.mark.unit
    def test_enroll_no_database(self) -> None:
        m = self._make_manager()
        ok, uri, codes = m.enroll_user("1001")
        assert ok is True
        assert uri is not None
        assert "otpauth://" in uri
        assert codes is not None
        assert len(codes) == 10

    @pytest.mark.unit
    def test_enroll_with_database_new_user(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db)
        ok, uri, codes = m.enroll_user("1001")
        assert ok is True
        assert uri is not None
        assert codes is not None

    @pytest.mark.unit
    def test_enroll_with_database_existing_user(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [{"id": 1, "enabled": True}]
        m = self._make_manager(db=db)
        ok, _uri, _codes = m.enroll_user("1001")
        assert ok is True

    @pytest.mark.unit
    def test_enroll_with_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db)
        ok, _uri, _codes = m.enroll_user("1001")
        assert ok is True

    @pytest.mark.unit
    def test_enroll_database_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db)
        ok, _uri, _codes = m.enroll_user("1001")
        assert ok is False


class TestMFAManagerVerifyEnrollment:
    """Tests for MFAManager.verify_enrollment."""

    def _make_manager(self, db=None, enabled=True, secret_bytes=None):
        config = {"security.mfa.enabled": enabled}
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            enc = MagicMock()
            mock_enc.return_value = enc
            from pbx.features.mfa import MFAManager

            m = MFAManager(database=db, config=config)
        if secret_bytes is not None:
            m._get_secret_for_enrollment = MagicMock(return_value=secret_bytes)
        return m

    @pytest.mark.unit
    def test_verify_enrollment_disabled(self) -> None:
        m = self._make_manager(enabled=False)
        assert m.verify_enrollment("1001", "123456") is False

    @pytest.mark.unit
    def test_verify_enrollment_no_secret(self) -> None:
        m = self._make_manager(enabled=True, secret_bytes=None)
        assert m.verify_enrollment("1001", "123456") is False

    @pytest.mark.unit
    def test_verify_enrollment_wrong_code(self) -> None:
        secret = b"A" * 20
        m = self._make_manager(enabled=True, secret_bytes=secret)
        assert m.verify_enrollment("1001", "000000") is False

    @pytest.mark.unit
    def test_verify_enrollment_correct_code(self) -> None:
        secret = b"A" * 20
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db, enabled=True, secret_bytes=secret)
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            totp = TOTPGenerator(secret=secret)
            code = totp.generate()
        assert m.verify_enrollment("1001", code) is True
        db.execute.assert_called()

    @pytest.mark.unit
    def test_verify_enrollment_correct_code_postgresql(self) -> None:
        secret = b"A" * 20
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        m = self._make_manager(db=db, enabled=True, secret_bytes=secret)
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            totp = TOTPGenerator(secret=secret)
            code = totp.generate()
        assert m.verify_enrollment("1001", code) is True

    @pytest.mark.unit
    def test_verify_enrollment_db_error(self) -> None:
        secret = b"A" * 20
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.execute.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db, enabled=True, secret_bytes=secret)
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            totp = TOTPGenerator(secret=secret)
            code = totp.generate()
        assert m.verify_enrollment("1001", code) is False


class TestMFAManagerVerifyCode:
    """Tests for MFAManager.verify_code."""

    def _make_manager(self, enabled=True, required=False, yubikey=False, db=None):
        config = {
            "security.mfa.enabled": enabled,
            "security.mfa.required": required,
            "security.mfa.yubikey.enabled": yubikey,
        }
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            enc = MagicMock()
            mock_enc.return_value = enc
            from pbx.features.mfa import MFAManager

            m = MFAManager(database=db, config=config)
        return m

    @pytest.mark.unit
    def test_verify_code_mfa_disabled(self) -> None:
        m = self._make_manager(enabled=False)
        assert m.verify_code("1001", "123456") is True

    @pytest.mark.unit
    def test_verify_code_user_not_enrolled_not_required(self) -> None:
        m = self._make_manager(enabled=True, required=False)
        m.is_enabled_for_user = MagicMock(return_value=False)
        assert m.verify_code("1001", "123456") is True

    @pytest.mark.unit
    def test_verify_code_user_not_enrolled_required(self) -> None:
        m = self._make_manager(enabled=True, required=True)
        m.is_enabled_for_user = MagicMock(return_value=False)
        assert m.verify_code("1001", "123456") is False

    @pytest.mark.unit
    def test_verify_code_totp_valid(self) -> None:
        secret = b"A" * 20
        m = self._make_manager(enabled=True)
        m.is_enabled_for_user = MagicMock(return_value=True)
        m._get_secret = MagicMock(return_value=secret)
        m._update_last_used = MagicMock()
        with patch("pbx.features.mfa.get_logger"):
            from pbx.features.mfa import TOTPGenerator

            code = TOTPGenerator(secret=secret).generate()
        assert m.verify_code("1001", code) is True
        m._update_last_used.assert_called_once_with("1001")

    @pytest.mark.unit
    def test_verify_code_totp_invalid_tries_backup(self) -> None:
        m = self._make_manager(enabled=True)
        m.is_enabled_for_user = MagicMock(return_value=True)
        m._get_secret = MagicMock(return_value=b"A" * 20)
        m._verify_backup_code = MagicMock(return_value=True)
        assert m.verify_code("1001", "BACKUP1") is True

    @pytest.mark.unit
    def test_verify_code_totp_invalid_backup_invalid(self) -> None:
        m = self._make_manager(enabled=True)
        m.is_enabled_for_user = MagicMock(return_value=True)
        m._get_secret = MagicMock(return_value=b"A" * 20)
        m._verify_backup_code = MagicMock(return_value=False)
        assert m.verify_code("1001", "WRONG") is False

    @pytest.mark.unit
    def test_verify_code_no_secret_tries_backup(self) -> None:
        m = self._make_manager(enabled=True)
        m.is_enabled_for_user = MagicMock(return_value=True)
        m._get_secret = MagicMock(return_value=None)
        m._verify_backup_code = MagicMock(return_value=True)
        assert m.verify_code("1001", "BACKUP1") is True

    @pytest.mark.unit
    def test_verify_code_yubikey_otp(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(enabled=True, yubikey=True, db=db)
        m.is_enabled_for_user = MagicMock(return_value=True)
        m._get_secret = MagicMock(return_value=b"A" * 20)
        m._verify_yubikey_otp = MagicMock(return_value=True)
        otp_44 = "c" * 44
        assert m.verify_code("1001", otp_44) is True

    @pytest.mark.unit
    def test_verify_code_exception(self) -> None:
        m = self._make_manager(enabled=True)
        m.is_enabled_for_user = MagicMock(return_value=True)
        m._get_secret = MagicMock(side_effect=RuntimeError("boom"))
        assert m.verify_code("1001", "123456") is False


class TestMFAManagerIsEnabledForUser:
    """Tests for MFAManager.is_enabled_for_user."""

    def _make_manager(self, enabled=True, db=None):
        config = {"security.mfa.enabled": enabled}
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager

            return MFAManager(database=db, config=config)

    @pytest.mark.unit
    def test_not_enabled(self) -> None:
        m = self._make_manager(enabled=False)
        assert m.is_enabled_for_user("1001") is False

    @pytest.mark.unit
    def test_no_database(self) -> None:
        m = self._make_manager(enabled=True)
        assert m.is_enabled_for_user("1001") is False

    @pytest.mark.unit
    def test_user_enabled(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [{"enabled": True}]
        m = self._make_manager(enabled=True, db=db)
        assert m.is_enabled_for_user("1001") is True

    @pytest.mark.unit
    def test_user_not_enabled(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [{"enabled": False}]
        m = self._make_manager(enabled=True, db=db)
        assert m.is_enabled_for_user("1001") is False

    @pytest.mark.unit
    def test_user_not_found(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = []
        m = self._make_manager(enabled=True, db=db)
        assert m.is_enabled_for_user("1001") is False

    @pytest.mark.unit
    def test_database_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.side_effect = sqlite3.Error("fail")
        m = self._make_manager(enabled=True, db=db)
        assert m.is_enabled_for_user("1001") is False

    @pytest.mark.unit
    def test_postgresql_query(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        db.fetch_all.return_value = [{"enabled": True}]
        m = self._make_manager(enabled=True, db=db)
        assert m.is_enabled_for_user("1001") is True


class TestMFAManagerDisableForUser:
    """Tests for MFAManager.disable_for_user."""

    def _make_manager(self, db=None):
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager

            return MFAManager(database=db, config={})

    @pytest.mark.unit
    def test_no_database(self) -> None:
        m = self._make_manager()
        assert m.disable_for_user("1001") is False

    @pytest.mark.unit
    def test_success_sqlite(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db)
        assert m.disable_for_user("1001") is True

    @pytest.mark.unit
    def test_success_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        m = self._make_manager(db=db)
        assert m.disable_for_user("1001") is True

    @pytest.mark.unit
    def test_database_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.execute.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db)
        assert m.disable_for_user("1001") is False


class TestMFAManagerEnrollYubikey:
    """Tests for MFAManager.enroll_yubikey."""

    def _make_manager(self, db=None, yubikey=True):
        config = {"security.mfa.yubikey.enabled": yubikey}
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager

            return MFAManager(database=db, config=config)

    @pytest.mark.unit
    def test_yubikey_not_enabled(self) -> None:
        m = self._make_manager(yubikey=False)
        ok, err = m.enroll_yubikey("1001", "c" * 44)
        assert ok is False
        assert "not enabled" in err.lower()

    @pytest.mark.unit
    def test_no_database(self) -> None:
        m = self._make_manager(yubikey=True)
        ok, err = m.enroll_yubikey("1001", "c" * 44)
        assert ok is False
        assert "Database" in err

    @pytest.mark.unit
    def test_otp_invalid(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.verify_otp.return_value = (False, "bad otp")
        ok, _err = m.enroll_yubikey("1001", "c" * 44)
        assert ok is False

    @pytest.mark.unit
    def test_cannot_extract_public_id(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.verify_otp.return_value = (True, None)
        m.yubikey_verifier.extract_public_id.return_value = None
        ok, err = m.enroll_yubikey("1001", "c" * 44)
        assert ok is False
        assert "public ID" in err

    @pytest.mark.unit
    def test_already_enrolled(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [{"id": 1}]
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.verify_otp.return_value = (True, None)
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        ok, err = m.enroll_yubikey("1001", "c" * 44)
        assert ok is False
        assert "already enrolled" in err.lower()

    @pytest.mark.unit
    def test_success(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.verify_otp.return_value = (True, None)
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        ok, err = m.enroll_yubikey("1001", "c" * 44, device_name="My Key")
        assert ok is True
        assert err is None

    @pytest.mark.unit
    def test_success_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.verify_otp.return_value = (True, None)
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        ok, _err = m.enroll_yubikey("1001", "c" * 44)
        assert ok is True

    @pytest.mark.unit
    def test_database_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.verify_otp.return_value = (True, None)
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        ok, _err = m.enroll_yubikey("1001", "c" * 44)
        assert ok is False


class TestMFAManagerEnrollFido2:
    """Tests for MFAManager.enroll_fido2."""

    def _make_manager(self, db=None, fido2=True):
        config = {"security.mfa.fido2.enabled": fido2}
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager

            return MFAManager(database=db, config=config)

    @pytest.mark.unit
    def test_fido2_not_enabled(self) -> None:
        m = self._make_manager(fido2=False)
        ok, err = m.enroll_fido2("1001", {})
        assert ok is False
        assert "not enabled" in err.lower()

    @pytest.mark.unit
    def test_no_database(self) -> None:
        m = self._make_manager(fido2=True)
        ok, err = m.enroll_fido2("1001", {})
        assert ok is False
        assert "Database" in err

    @pytest.mark.unit
    def test_registration_fails(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db, fido2=True)
        m.fido2_verifier = MagicMock()
        m.fido2_verifier.register_credential.return_value = (False, "bad credential")
        ok, err = m.enroll_fido2("1001", {"credential_id": "cid", "public_key": "pk"})
        assert ok is False
        assert "bad credential" in err

    @pytest.mark.unit
    def test_success_string_public_key(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db, fido2=True)
        m.fido2_verifier = MagicMock()
        m.fido2_verifier.register_credential.return_value = (True, "cred_id_123")
        ok, _err = m.enroll_fido2(
            "1001",
            {
                "credential_id": "cred_id_123",
                "public_key": "string_pk",
            },
        )
        assert ok is True

    @pytest.mark.unit
    def test_success_dict_public_key(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db, fido2=True)
        m.fido2_verifier = MagicMock()
        m.fido2_verifier.register_credential.return_value = (True, "cred_id_123")
        ok, _err = m.enroll_fido2(
            "1001",
            {
                "credential_id": "cred_id_123",
                "public_key": {"kty": "EC"},
            },
        )
        assert ok is True

    @pytest.mark.unit
    def test_success_bytes_public_key(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db, fido2=True)
        m.fido2_verifier = MagicMock()
        m.fido2_verifier.register_credential.return_value = (True, "cred_id_123")
        ok, _err = m.enroll_fido2(
            "1001",
            {
                "credential_id": "cred_id_123",
                "public_key": b"bytes_pk",
            },
        )
        assert ok is True

    @pytest.mark.unit
    def test_success_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        m = self._make_manager(db=db, fido2=True)
        m.fido2_verifier = MagicMock()
        m.fido2_verifier.register_credential.return_value = (True, "cred_id_123")
        ok, _err = m.enroll_fido2(
            "1001",
            {
                "credential_id": "cred_id_123",
                "public_key": "pk",
            },
        )
        assert ok is True

    @pytest.mark.unit
    def test_database_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.execute.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db, fido2=True)
        m.fido2_verifier = MagicMock()
        m.fido2_verifier.register_credential.return_value = (True, "cred_id_123")
        ok, _err = m.enroll_fido2(
            "1001",
            {
                "credential_id": "cred_id_123",
                "public_key": "pk",
            },
        )
        assert ok is False


class TestMFAManagerGetEnrolledMethods:
    """Tests for MFAManager.get_enrolled_methods."""

    def _make_manager(self, db=None, yubikey=False, fido2=False):
        config = {
            "security.mfa.yubikey.enabled": yubikey,
            "security.mfa.fido2.enabled": fido2,
        }
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager

            return MFAManager(database=db, config=config)

    @pytest.mark.unit
    def test_no_database(self) -> None:
        m = self._make_manager()
        methods = m.get_enrolled_methods("1001")
        assert methods["totp"] is False
        assert methods["yubikeys"] == []
        assert methods["fido2"] == []
        assert methods["backup_codes"] == 0

    @pytest.mark.unit
    def test_with_database(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [{"enabled": True}]
        db.fetch_one.return_value = {"count": 5}
        m = self._make_manager(db=db)
        methods = m.get_enrolled_methods("1001")
        assert methods["totp"] is True
        assert methods["backup_codes"] == 5

    @pytest.mark.unit
    def test_with_yubikeys(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"

        def fetch_all_side(query, params):
            if "mfa_yubikey_devices" in query:
                return [{"public_id": "cccc", "device_name": "key1", "enrolled_at": "2024-01-01"}]
            if "mfa_secrets" in query:
                return [{"enabled": True}]
            return []

        db.fetch_all.side_effect = fetch_all_side
        db.fetch_one.return_value = {"count": 3}
        m = self._make_manager(db=db, yubikey=True)
        methods = m.get_enrolled_methods("1001")
        assert len(methods["yubikeys"]) == 1

    @pytest.mark.unit
    def test_with_fido2(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"

        def fetch_all_side(query, params):
            if "mfa_fido2_credentials" in query:
                return [{"credential_id": "cid", "device_name": "key", "enrolled_at": "2024"}]
            if "mfa_secrets" in query:
                return [{"enabled": False}]
            return []

        db.fetch_all.side_effect = fetch_all_side
        db.fetch_one.return_value = {"count": 0}
        m = self._make_manager(db=db, fido2=True)
        methods = m.get_enrolled_methods("1001")
        assert len(methods["fido2"]) == 1

    @pytest.mark.unit
    def test_fetch_one_none(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = []
        db.fetch_one.return_value = None
        m = self._make_manager(db=db)
        methods = m.get_enrolled_methods("1001")
        assert methods["backup_codes"] == 0

    @pytest.mark.unit
    def test_database_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db)
        methods = m.get_enrolled_methods("1001")
        assert methods["totp"] is False

    @pytest.mark.unit
    def test_postgresql_queries(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        db.fetch_all.return_value = [{"enabled": True}]
        db.fetch_one.return_value = {"count": 2}
        m = self._make_manager(db=db, yubikey=True, fido2=True)
        methods = m.get_enrolled_methods("1001")
        assert methods["totp"] is True


class TestMFAManagerPrivateMethods:
    """Tests for MFAManager private helper methods."""

    def _make_manager(self, db=None, enabled=True, yubikey=False):
        config = {
            "security.mfa.enabled": enabled,
            "security.mfa.yubikey.enabled": yubikey,
        }
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            enc = MagicMock()
            mock_enc.return_value = enc
            from pbx.features.mfa import MFAManager

            m = MFAManager(database=db, config=config)
        return m

    # _verify_yubikey_otp tests
    @pytest.mark.unit
    def test_verify_yubikey_otp_not_enabled(self) -> None:
        m = self._make_manager(yubikey=False)
        assert m._verify_yubikey_otp("1001", "c" * 44) is False

    @pytest.mark.unit
    def test_verify_yubikey_otp_no_database(self) -> None:
        m = self._make_manager(yubikey=True)
        assert m._verify_yubikey_otp("1001", "c" * 44) is False

    @pytest.mark.unit
    def test_verify_yubikey_otp_no_public_id(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.extract_public_id.return_value = None
        assert m._verify_yubikey_otp("1001", "c" * 44) is False

    @pytest.mark.unit
    def test_verify_yubikey_otp_device_not_enrolled(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        assert m._verify_yubikey_otp("1001", "c" * 44) is False

    @pytest.mark.unit
    def test_verify_yubikey_otp_valid(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [{"id": 1}]
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        m.yubikey_verifier.verify_otp.return_value = (True, None)
        assert m._verify_yubikey_otp("1001", "c" * 44) is True

    @pytest.mark.unit
    def test_verify_yubikey_otp_invalid(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [{"id": 1}]
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        m.yubikey_verifier.verify_otp.return_value = (False, "bad")
        assert m._verify_yubikey_otp("1001", "c" * 44) is False

    @pytest.mark.unit
    def test_verify_yubikey_otp_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        db.fetch_all.return_value = [{"id": 1}]
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        m.yubikey_verifier.verify_otp.return_value = (True, None)
        assert m._verify_yubikey_otp("1001", "c" * 44) is True

    @pytest.mark.unit
    def test_verify_yubikey_otp_db_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db, yubikey=True)
        m.yubikey_verifier = MagicMock()
        m.yubikey_verifier.extract_public_id.return_value = "cccccccccccc"
        assert m._verify_yubikey_otp("1001", "c" * 44) is False

    # _get_secret tests
    @pytest.mark.unit
    def test_get_secret_no_database(self) -> None:
        m = self._make_manager()
        assert m._get_secret("1001") is None

    @pytest.mark.unit
    def test_get_secret_no_result(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db)
        assert m._get_secret("1001") is None

    @pytest.mark.unit
    def test_get_secret_success(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        # Build valid encrypted data
        nonce = "bm9uY2U="  # base64("nonce")
        tag = "dGFn"  # base64("tag")
        enc_data = "ZW5j"  # base64("enc")
        combined = nonce.encode() + b"|" + tag.encode() + b"|" + enc_data.encode()
        encrypted_b64 = base64.b64encode(combined).decode("utf-8")
        salt_b64 = base64.b64encode(b"salt" * 8).decode("utf-8")
        db.fetch_all.return_value = [{"secret_encrypted": encrypted_b64, "secret_salt": salt_b64}]
        m = self._make_manager(db=db)
        m.encryption.derive_key.return_value = (b"k" * 32, b"salt" * 8)
        m.encryption.decrypt_data.return_value = b"decrypted_secret"
        result = m._get_secret("1001")
        assert result == b"decrypted_secret"

    @pytest.mark.unit
    def test_get_secret_invalid_format(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        # Missing a pipe separator => less than 3 parts
        combined = b"only_one_part"
        encrypted_b64 = base64.b64encode(combined).decode("utf-8")
        salt_b64 = base64.b64encode(b"salt" * 8).decode("utf-8")
        db.fetch_all.return_value = [{"secret_encrypted": encrypted_b64, "secret_salt": salt_b64}]
        m = self._make_manager(db=db)
        m.encryption.derive_key.return_value = (b"k" * 32, b"salt" * 8)
        assert m._get_secret("1001") is None

    @pytest.mark.unit
    def test_get_secret_db_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db)
        assert m._get_secret("1001") is None

    @pytest.mark.unit
    def test_get_secret_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db)
        assert m._get_secret("1001") is None

    # _get_secret_for_enrollment tests
    @pytest.mark.unit
    def test_get_secret_for_enrollment_no_database(self) -> None:
        m = self._make_manager()
        assert m._get_secret_for_enrollment("1001") is None

    @pytest.mark.unit
    def test_get_secret_for_enrollment_no_result(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db)
        assert m._get_secret_for_enrollment("1001") is None

    @pytest.mark.unit
    def test_get_secret_for_enrollment_success(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        nonce = "bm9uY2U="
        tag = "dGFn"
        enc_data = "ZW5j"
        combined = nonce.encode() + b"|" + tag.encode() + b"|" + enc_data.encode()
        encrypted_b64 = base64.b64encode(combined).decode("utf-8")
        salt_b64 = base64.b64encode(b"salt" * 8).decode("utf-8")
        db.fetch_all.return_value = [{"secret_encrypted": encrypted_b64, "secret_salt": salt_b64}]
        m = self._make_manager(db=db)
        m.encryption.derive_key.return_value = (b"k" * 32, b"salt" * 8)
        m.encryption.decrypt_data.return_value = b"my_secret"
        result = m._get_secret_for_enrollment("1001")
        assert result == b"my_secret"

    @pytest.mark.unit
    def test_get_secret_for_enrollment_invalid_format(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        combined = b"nopipe"
        encrypted_b64 = base64.b64encode(combined).decode("utf-8")
        salt_b64 = base64.b64encode(b"salt" * 8).decode("utf-8")
        db.fetch_all.return_value = [{"secret_encrypted": encrypted_b64, "secret_salt": salt_b64}]
        m = self._make_manager(db=db)
        m.encryption.derive_key.return_value = (b"k" * 32, b"salt" * 8)
        assert m._get_secret_for_enrollment("1001") is None

    @pytest.mark.unit
    def test_get_secret_for_enrollment_db_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.side_effect = ValueError("fail")
        m = self._make_manager(db=db)
        assert m._get_secret_for_enrollment("1001") is None

    @pytest.mark.unit
    def test_get_secret_for_enrollment_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db)
        assert m._get_secret_for_enrollment("1001") is None

    # _verify_backup_code tests
    @pytest.mark.unit
    def test_verify_backup_code_no_database(self) -> None:
        m = self._make_manager()
        assert m._verify_backup_code("1001", "ABCD-EFGH") is False

    @pytest.mark.unit
    def test_verify_backup_code_no_codes(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = []
        m = self._make_manager(db=db)
        assert m._verify_backup_code("1001", "ABCD-EFGH") is False

    @pytest.mark.unit
    def test_verify_backup_code_match(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [
            {"id": 1, "code_hash": "hash1", "code_salt": "salt1"},
        ]
        m = self._make_manager(db=db)
        m.encryption.verify_password.return_value = True
        assert m._verify_backup_code("1001", "ABCD-EFGH") is True
        db.execute.assert_called()

    @pytest.mark.unit
    def test_verify_backup_code_no_match(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.return_value = [
            {"id": 1, "code_hash": "hash1", "code_salt": "salt1"},
        ]
        m = self._make_manager(db=db)
        m.encryption.verify_password.return_value = False
        assert m._verify_backup_code("1001", "XXXX-XXXX") is False

    @pytest.mark.unit
    def test_verify_backup_code_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        db.fetch_all.return_value = [
            {"id": 1, "code_hash": "hash1", "code_salt": "salt1"},
        ]
        m = self._make_manager(db=db)
        m.encryption.verify_password.return_value = True
        assert m._verify_backup_code("1001", "ABCD-EFGH") is True

    @pytest.mark.unit
    def test_verify_backup_code_db_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.fetch_all.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db)
        assert m._verify_backup_code("1001", "ABCD-EFGH") is False

    # _update_last_used tests
    @pytest.mark.unit
    def test_update_last_used_no_database(self) -> None:
        m = self._make_manager()
        m._update_last_used("1001")  # Should not raise

    @pytest.mark.unit
    def test_update_last_used_success(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        m = self._make_manager(db=db)
        m._update_last_used("1001")
        db.execute.assert_called()

    @pytest.mark.unit
    def test_update_last_used_postgresql(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "postgresql"
        m = self._make_manager(db=db)
        m._update_last_used("1001")
        db.execute.assert_called()

    @pytest.mark.unit
    def test_update_last_used_db_error(self) -> None:
        db = MagicMock()
        db.enabled = True
        db.db_type = "sqlite"
        db.execute.side_effect = sqlite3.Error("fail")
        m = self._make_manager(db=db)
        m._update_last_used("1001")  # Should not raise

    # _generate_backup_codes tests
    @pytest.mark.unit
    def test_generate_backup_codes_default_count(self) -> None:
        m = self._make_manager()
        codes = m._generate_backup_codes()
        assert len(codes) == 10
        for code in codes:
            assert len(code) == 9  # XXXX-XXXX
            assert code[4] == "-"

    @pytest.mark.unit
    def test_generate_backup_codes_custom_count(self) -> None:
        m = self._make_manager()
        codes = m._generate_backup_codes(count=5)
        assert len(codes) == 5

    @pytest.mark.unit
    def test_generate_backup_codes_valid_chars(self) -> None:
        m = self._make_manager()
        valid_chars = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789-")
        codes = m._generate_backup_codes()
        for code in codes:
            assert all(c in valid_chars for c in code)

    @pytest.mark.unit
    def test_generate_backup_codes_no_confusing_chars(self) -> None:
        """Backup codes should not contain 0, O, I, or 1."""
        m = self._make_manager()
        confusing = set("0OI1")
        codes = m._generate_backup_codes(count=50)
        for code in codes:
            assert not any(c in confusing for c in code)


# ---------------------------------------------------------------------------
# get_mfa_manager tests
# ---------------------------------------------------------------------------
class TestGetMfaManager:
    """Tests for the get_mfa_manager factory function."""

    @pytest.mark.unit
    def test_returns_mfa_manager(self) -> None:
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import MFAManager, get_mfa_manager

            m = get_mfa_manager()
            assert isinstance(m, MFAManager)

    @pytest.mark.unit
    def test_passes_arguments(self) -> None:
        db = MagicMock()
        db.enabled = False
        config = {"security.mfa.enabled": False}
        with (
            patch("pbx.features.mfa.get_logger"),
            patch("pbx.features.mfa.get_encryption") as mock_enc,
        ):
            mock_enc.return_value = MagicMock()
            from pbx.features.mfa import get_mfa_manager

            m = get_mfa_manager(database=db, config=config)
            assert m.database is db
            assert m.enabled is False
