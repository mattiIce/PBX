"""Comprehensive tests for pbx/utils/tls_support.py - TLS support."""

import ssl
from unittest.mock import MagicMock, patch

import pytest

from pbx.utils.tls_support import SRTPManager, TLSManager, generate_srtp_keys


@pytest.mark.unit
class TestTLSManagerInit:
    """Tests for TLSManager.__init__."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_init_without_certs(self, mock_get_logger: MagicMock) -> None:
        mgr = TLSManager()
        assert mgr.cert_file is None
        assert mgr.key_file is None
        assert mgr.fips_mode is False
        assert mgr.ssl_context is None

    @patch("pbx.utils.tls_support.get_logger")
    def test_init_with_only_cert_file(self, mock_get_logger: MagicMock) -> None:
        mgr = TLSManager(cert_file="/path/to/cert.pem")
        assert mgr.cert_file == "/path/to/cert.pem"
        assert mgr.key_file is None
        # Only cert_file but no key_file -> _create_ssl_context not called
        assert mgr.ssl_context is None

    @patch("pbx.utils.tls_support.get_logger")
    def test_init_with_only_key_file(self, mock_get_logger: MagicMock) -> None:
        mgr = TLSManager(key_file="/path/to/key.pem")
        assert mgr.key_file == "/path/to/key.pem"
        assert mgr.cert_file is None
        assert mgr.ssl_context is None

    @patch("pbx.utils.tls_support.get_logger")
    def test_init_fips_mode_flag(self, mock_get_logger: MagicMock) -> None:
        mgr = TLSManager(fips_mode=True)
        assert mgr.fips_mode is True

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_init_with_cert_and_key_creates_context(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        mgr = TLSManager(cert_file="/path/cert.pem", key_file="/path/key.pem")
        assert mgr.ssl_context is not None
        mock_ctx.load_cert_chain.assert_called_once_with("/path/cert.pem", "/path/key.pem")


@pytest.mark.unit
class TestTLSManagerCreateSSLContext:
    """Tests for TLSManager._create_ssl_context."""

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_creates_tls_server_context(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        mock_ssl_context_cls.assert_called_once_with(ssl.PROTOCOL_TLS_SERVER)

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_non_fips_mode_ciphers(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        TLSManager(cert_file="/cert.pem", key_file="/key.pem", fips_mode=False)
        mock_ctx.set_ciphers.assert_called_once_with(
            "HIGH:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4"
        )

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_fips_mode_ciphers(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        TLSManager(cert_file="/cert.pem", key_file="/key.pem", fips_mode=True)
        call_args = mock_ctx.set_ciphers.call_args[0][0]
        assert "ECDHE-RSA-AES256-GCM-SHA384" in call_args
        assert "ECDHE-RSA-AES128-GCM-SHA256" in call_args
        assert "AES256-GCM-SHA384" in call_args
        assert "AES128-GCM-SHA256" in call_args

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_minimum_tls_version_set(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        assert mock_ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_fips_minimum_tls_version_set(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        TLSManager(cert_file="/cert.pem", key_file="/key.pem", fips_mode=True)
        assert mock_ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_disables_old_protocols(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        # After init, options should include all the disabled protocol flags
        expected_options = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        assert (mock_ctx.options & expected_options) == expected_options

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_ssl_error_sets_context_to_none(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ctx.load_cert_chain.side_effect = ssl.SSLError("bad cert")
        mock_ssl_context_cls.return_value = mock_ctx
        mgr = TLSManager(cert_file="/bad/cert.pem", key_file="/bad/key.pem")
        assert mgr.ssl_context is None

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_os_error_sets_context_to_none(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ctx.load_cert_chain.side_effect = OSError("file not found")
        mock_ssl_context_cls.return_value = mock_ctx
        mgr = TLSManager(cert_file="/bad/cert.pem", key_file="/bad/key.pem")
        assert mgr.ssl_context is None

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_logs_info_on_success(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        mock_logger.info.assert_called()

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_logs_error_on_failure(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ctx.load_cert_chain.side_effect = ssl.SSLError("bad cert")
        mock_ssl_context_cls.return_value = mock_ctx
        TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        mock_logger.error.assert_called()


@pytest.mark.unit
class TestTLSManagerWrapSocket:
    """Tests for TLSManager.wrap_socket."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_wrap_socket_no_context_returns_none(self, mock_get_logger: MagicMock) -> None:
        mgr = TLSManager()
        result = mgr.wrap_socket(MagicMock())
        assert result is None

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_wrap_socket_success(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_socket = MagicMock(spec=ssl.SSLSocket)
        mock_ctx.wrap_socket.return_value = mock_ssl_socket
        mock_ssl_context_cls.return_value = mock_ctx

        mgr = TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        sock = MagicMock()
        result = mgr.wrap_socket(sock, server_side=True)
        assert result is mock_ssl_socket
        mock_ctx.wrap_socket.assert_called_once_with(
            sock, server_side=True, do_handshake_on_connect=True
        )

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_wrap_socket_client_side(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_socket = MagicMock(spec=ssl.SSLSocket)
        mock_ctx.wrap_socket.return_value = mock_ssl_socket
        mock_ssl_context_cls.return_value = mock_ctx

        mgr = TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        sock = MagicMock()
        result = mgr.wrap_socket(sock, server_side=False)
        assert result is mock_ssl_socket
        mock_ctx.wrap_socket.assert_called_once_with(
            sock, server_side=False, do_handshake_on_connect=True
        )

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_wrap_socket_ssl_error_returns_none(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ctx.wrap_socket.side_effect = ssl.SSLError("handshake failed")
        mock_ssl_context_cls.return_value = mock_ctx

        mgr = TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        result = mgr.wrap_socket(MagicMock())
        assert result is None

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_wrap_socket_os_error_returns_none(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ctx.wrap_socket.side_effect = OSError("socket error")
        mock_ssl_context_cls.return_value = mock_ctx

        mgr = TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        result = mgr.wrap_socket(MagicMock())
        assert result is None


@pytest.mark.unit
class TestTLSManagerIsAvailable:
    """Tests for TLSManager.is_available."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_not_available_without_context(self, mock_get_logger: MagicMock) -> None:
        mgr = TLSManager()
        assert mgr.is_available() is False

    @patch("pbx.utils.tls_support.get_logger")
    @patch("ssl.SSLContext")
    def test_available_with_context(
        self, mock_ssl_context_cls: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_ctx = MagicMock()
        mock_ctx.options = 0
        mock_ssl_context_cls.return_value = mock_ctx
        mgr = TLSManager(cert_file="/cert.pem", key_file="/key.pem")
        assert mgr.is_available() is True


@pytest.mark.unit
class TestSRTPManagerInit:
    """Tests for SRTPManager.__init__."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_default_init(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        assert mgr.fips_mode is False
        assert mgr.sessions == {}

    @patch("pbx.utils.tls_support.get_logger")
    def test_fips_mode_init(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager(fips_mode=True)
        assert mgr.fips_mode is True

    @patch("pbx.utils.tls_support.CRYPTO_AVAILABLE", False)
    @patch("pbx.utils.tls_support.get_logger")
    def test_warns_when_crypto_not_available(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        SRTPManager()
        mock_logger.warning.assert_called()


@pytest.mark.unit
class TestSRTPManagerCreateSession:
    """Tests for SRTPManager.create_session."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_create_session_success(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        key = b"\x00" * 32
        salt = b"\x01" * 14
        result = mgr.create_session("call-1", key, salt)
        assert result is True
        assert "call-1" in mgr.sessions

    @patch("pbx.utils.tls_support.get_logger")
    def test_create_session_stores_key_and_salt(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        key = b"\xaa" * 32
        salt = b"\xbb" * 14
        mgr.create_session("call-1", key, salt)
        session = mgr.sessions["call-1"]
        assert session["master_key"] == key
        assert session["master_salt"] == salt
        assert session["cipher"] is not None

    @patch("pbx.utils.tls_support.CRYPTO_AVAILABLE", False)
    @patch("pbx.utils.tls_support.get_logger")
    def test_create_session_fails_without_crypto(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        result = mgr.create_session("call-1", b"\x00" * 32, b"\x01" * 14)
        assert result is False

    @patch("pbx.utils.tls_support.get_logger")
    @patch("pbx.utils.tls_support.AESGCM")
    def test_create_session_exception_returns_false(
        self, mock_aesgcm: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        mock_aesgcm.side_effect = ValueError("bad key")
        mgr = SRTPManager()
        result = mgr.create_session("call-1", b"\x00" * 16, b"\x01" * 14)
        assert result is False


@pytest.mark.unit
class TestSRTPManagerEncryptRtpPacket:
    """Tests for SRTPManager.encrypt_rtp_packet."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_encrypt_no_session_returns_none(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        result = mgr.encrypt_rtp_packet("nonexistent", b"\x00" * 100, 1)
        assert result is None

    @patch("pbx.utils.tls_support.get_logger")
    def test_encrypt_success(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        key = b"\x00" * 32
        salt = b"\x01" * 14
        mgr.create_session("call-1", key, salt)
        rtp_data = b"\x80\x00\x00\x01" + b"\x00" * 160
        result = mgr.encrypt_rtp_packet("call-1", rtp_data, 1)
        assert result is not None
        assert isinstance(result, bytes)
        assert result != rtp_data  # Should be different from original

    @patch("pbx.utils.tls_support.get_logger")
    def test_encrypt_different_sequence_numbers(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        key = b"\x00" * 32
        salt = b"\x01" * 14
        mgr.create_session("call-1", key, salt)
        rtp_data = b"\x80\x00\x00\x01" + b"\x00" * 160
        result1 = mgr.encrypt_rtp_packet("call-1", rtp_data, 1)
        result2 = mgr.encrypt_rtp_packet("call-1", rtp_data, 2)
        assert result1 is not None
        assert result2 is not None
        # Different sequence numbers -> different nonces -> different ciphertext
        assert result1 != result2

    @patch("pbx.utils.tls_support.get_logger")
    def test_encrypt_exception_returns_none(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        # Manually create a bad session
        mgr.sessions["call-1"] = {
            "master_key": b"\x00" * 32,
            "master_salt": b"\x01" * 14,
            "cipher": MagicMock(encrypt=MagicMock(side_effect=ValueError("encrypt failed"))),
        }
        result = mgr.encrypt_rtp_packet("call-1", b"\x00" * 100, 1)
        assert result is None


@pytest.mark.unit
class TestSRTPManagerDecryptRtpPacket:
    """Tests for SRTPManager.decrypt_rtp_packet."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_decrypt_no_session_returns_none(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        result = mgr.decrypt_rtp_packet("nonexistent", b"\x00" * 100, 1)
        assert result is None

    @patch("pbx.utils.tls_support.get_logger")
    def test_encrypt_then_decrypt_round_trip(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        key = b"\x00" * 32
        salt = b"\x01" * 14
        mgr.create_session("call-1", key, salt)
        original = b"\x80\x00\x00\x01" + b"\xaa" * 160
        encrypted = mgr.encrypt_rtp_packet("call-1", original, 42)
        assert encrypted is not None
        decrypted = mgr.decrypt_rtp_packet("call-1", encrypted, 42)
        assert decrypted == original

    @patch("pbx.utils.tls_support.get_logger")
    def test_decrypt_wrong_sequence_number_fails(self, mock_get_logger: MagicMock) -> None:
        from cryptography.exceptions import InvalidTag

        mgr = SRTPManager()
        key = b"\x00" * 32
        salt = b"\x01" * 14
        mgr.create_session("call-1", key, salt)
        original = b"\x80\x00\x00\x01" + b"\xaa" * 160
        encrypted = mgr.encrypt_rtp_packet("call-1", original, 42)
        assert encrypted is not None
        # Wrong sequence number -> wrong nonce -> AES-GCM raises InvalidTag
        with pytest.raises(InvalidTag):
            mgr.decrypt_rtp_packet("call-1", encrypted, 99)

    @patch("pbx.utils.tls_support.get_logger")
    def test_decrypt_exception_returns_none(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        mgr.sessions["call-1"] = {
            "master_key": b"\x00" * 32,
            "master_salt": b"\x01" * 14,
            "cipher": MagicMock(decrypt=MagicMock(side_effect=ValueError("decrypt failed"))),
        }
        result = mgr.decrypt_rtp_packet("call-1", b"\x00" * 100, 1)
        assert result is None


@pytest.mark.unit
class TestSRTPManagerDeriveNonce:
    """Tests for SRTPManager._derive_nonce."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_nonce_is_12_bytes(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        salt = b"\x01" * 14
        nonce = mgr._derive_nonce(salt, 0)
        assert len(nonce) == 12

    @patch("pbx.utils.tls_support.get_logger")
    def test_nonce_deterministic(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        salt = b"\x01" * 14
        nonce1 = mgr._derive_nonce(salt, 100)
        nonce2 = mgr._derive_nonce(salt, 100)
        assert nonce1 == nonce2

    @patch("pbx.utils.tls_support.get_logger")
    def test_nonce_different_for_different_seq(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        salt = b"\x01" * 14
        nonce1 = mgr._derive_nonce(salt, 1)
        nonce2 = mgr._derive_nonce(salt, 2)
        assert nonce1 != nonce2

    @patch("pbx.utils.tls_support.get_logger")
    def test_nonce_different_for_different_salt(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        salt1 = b"\x01" * 14
        salt2 = b"\x02" * 14
        nonce1 = mgr._derive_nonce(salt1, 1)
        nonce2 = mgr._derive_nonce(salt2, 1)
        assert nonce1 != nonce2

    @patch("pbx.utils.tls_support.get_logger")
    def test_nonce_zero_sequence(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        salt = b"\x01" * 14
        nonce = mgr._derive_nonce(salt, 0)
        assert isinstance(nonce, bytes)
        assert len(nonce) == 12

    @patch("pbx.utils.tls_support.get_logger")
    def test_nonce_large_sequence_number(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        salt = b"\x01" * 14
        nonce = mgr._derive_nonce(salt, 65535)
        assert isinstance(nonce, bytes)
        assert len(nonce) == 12


@pytest.mark.unit
class TestSRTPManagerCloseSession:
    """Tests for SRTPManager.close_session."""

    @patch("pbx.utils.tls_support.get_logger")
    def test_close_existing_session(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        key = b"\x00" * 32
        salt = b"\x01" * 14
        mgr.create_session("call-1", key, salt)
        assert "call-1" in mgr.sessions
        mgr.close_session("call-1")
        assert "call-1" not in mgr.sessions

    @patch("pbx.utils.tls_support.get_logger")
    def test_close_nonexistent_session_no_error(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        # Should not raise an exception
        mgr.close_session("nonexistent")
        assert "nonexistent" not in mgr.sessions

    @patch("pbx.utils.tls_support.get_logger")
    def test_close_session_logs_info(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mgr = SRTPManager()
        key = b"\x00" * 32
        salt = b"\x01" * 14
        mgr.create_session("call-1", key, salt)
        mgr.close_session("call-1")
        # Should have logged the close
        assert any("Closed" in str(c) for c in mock_logger.info.call_args_list)


@pytest.mark.unit
class TestSRTPManagerIsAvailable:
    """Tests for SRTPManager.is_available."""

    @patch("pbx.utils.tls_support.CRYPTO_AVAILABLE", True)
    @patch("pbx.utils.tls_support.get_logger")
    def test_available_when_crypto_present(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        assert mgr.is_available() is True

    @patch("pbx.utils.tls_support.CRYPTO_AVAILABLE", False)
    @patch("pbx.utils.tls_support.get_logger")
    def test_not_available_when_crypto_missing(self, mock_get_logger: MagicMock) -> None:
        mgr = SRTPManager()
        assert mgr.is_available() is False


@pytest.mark.unit
class TestGenerateSrtpKeys:
    """Tests for generate_srtp_keys."""

    def test_returns_tuple(self) -> None:
        result = generate_srtp_keys()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_master_key_is_32_bytes(self) -> None:
        key, _ = generate_srtp_keys()
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_master_salt_is_14_bytes(self) -> None:
        _, salt = generate_srtp_keys()
        assert isinstance(salt, bytes)
        assert len(salt) == 14

    def test_keys_are_random(self) -> None:
        key1, salt1 = generate_srtp_keys()
        key2, salt2 = generate_srtp_keys()
        # Cryptographically random keys should (almost certainly) be different
        assert key1 != key2
        assert salt1 != salt2

    def test_keys_usable_for_session(self) -> None:
        key, salt = generate_srtp_keys()
        with patch("pbx.utils.tls_support.get_logger"):
            mgr = SRTPManager()
            result = mgr.create_session("call-test", key, salt)
            assert result is True
