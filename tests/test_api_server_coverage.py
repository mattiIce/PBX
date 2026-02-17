"""Comprehensive tests for PBXFlaskServer (pbx/api/server.py)."""

import ssl
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pbx.api.server import PBXFlaskServer


def _make_pbx_core(ssl_enabled=False, cert_file=None, key_file=None, ca_config=None):
    """Create a mock PBXCore with config."""
    pbx_core = MagicMock()
    ssl_config = {
        "enabled": ssl_enabled,
        "cert_file": cert_file,
        "key_file": key_file,
    }
    if ca_config:
        ssl_config["ca"] = ca_config
    else:
        ssl_config["ca"] = {"enabled": False}

    def config_get(key, default=None):
        if key == "api.ssl":
            return ssl_config
        if key == "api.ssl.enabled":
            return ssl_enabled
        return default

    pbx_core.config.get.side_effect = config_get
    return pbx_core


@pytest.mark.unit
class TestPBXFlaskServerInit:
    """Tests for PBXFlaskServer initialization."""

    def test_init_default_params(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        assert server.host == "0.0.0.0"
        assert server.port == 9000
        assert server.running is False
        assert server.ssl_enabled is False
        assert server.ssl_context is None
        assert server.app is not None

    def test_init_custom_params(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core, host="127.0.0.1", port=8080)
        assert server.host == "127.0.0.1"
        assert server.port == 8080

    def test_init_sets_pbx_core(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        assert server.pbx_core is pbx_core

    def test_init_creates_flask_app(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        assert server.app is not None
        assert server.app.config["PBX_CORE"] is pbx_core


@pytest.mark.unit
class TestConfigureSSL:
    """Tests for SSL configuration."""

    def test_ssl_disabled(self) -> None:
        pbx_core = _make_pbx_core(ssl_enabled=False)
        server = PBXFlaskServer(pbx_core)
        assert server.ssl_enabled is False
        assert server.ssl_context is None

    def test_ssl_enabled_no_cert_file(self) -> None:
        pbx_core = _make_pbx_core(ssl_enabled=True, cert_file=None, key_file=None)
        server = PBXFlaskServer(pbx_core)
        assert server.ssl_enabled is False

    def test_ssl_enabled_cert_not_found(self, tmp_path: Path) -> None:
        cert_file = str(tmp_path / "nonexistent.crt")
        key_file = str(tmp_path / "nonexistent.key")
        pbx_core = _make_pbx_core(ssl_enabled=True, cert_file=cert_file, key_file=key_file)
        server = PBXFlaskServer(pbx_core)
        assert server.ssl_enabled is False

    def test_ssl_enabled_key_not_found(self, tmp_path: Path) -> None:
        cert_file = tmp_path / "server.crt"
        cert_file.write_text("cert data")
        key_file = str(tmp_path / "nonexistent.key")
        pbx_core = _make_pbx_core(
            ssl_enabled=True, cert_file=str(cert_file), key_file=key_file
        )
        server = PBXFlaskServer(pbx_core)
        assert server.ssl_enabled is False

    def test_ssl_enabled_valid_certs(self, tmp_path: Path) -> None:
        # Create mock cert/key files (invalid SSL but tests the path logic)
        cert_file = tmp_path / "server.crt"
        key_file = tmp_path / "server.key"
        cert_file.write_text("cert")
        key_file.write_text("key")

        pbx_core = _make_pbx_core(
            ssl_enabled=True, cert_file=str(cert_file), key_file=str(key_file)
        )
        # The ssl.SSLContext.load_cert_chain will fail with invalid certs,
        # so ssl_enabled will remain False due to the exception handler
        server = PBXFlaskServer(pbx_core)
        # It should not crash - just log error and continue
        assert server.ssl_enabled is False

    def test_ssl_with_ca_enabled_cert_missing(self, tmp_path: Path) -> None:
        cert_file = str(tmp_path / "server.crt")
        key_file = str(tmp_path / "server.key")
        ca_config = {"enabled": True, "url": "https://ca.example.com", "token": "tok"}

        pbx_core = _make_pbx_core(
            ssl_enabled=True,
            cert_file=cert_file,
            key_file=key_file,
            ca_config=ca_config,
        )
        with patch.object(
            PBXFlaskServer, "_request_certificate_from_ca", return_value=False
        ):
            server = PBXFlaskServer(pbx_core)
        # Cert file doesn't exist after failed CA request, so SSL remains off
        assert server.ssl_enabled is False


@pytest.mark.unit
class TestRequestCertificateFromCA:
    """Tests for _request_certificate_from_ca."""

    def test_no_ca_url(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        result = server._request_certificate_from_ca({}, None, None)
        assert result is False

    def test_successful_request(self, tmp_path: Path) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        cert_file = str(tmp_path / "server.crt")
        key_file = str(tmp_path / "server.key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "certificate": "---CERT---",
            "private_key": "---KEY---",
        }

        with patch("requests.post", return_value=mock_response):
            result = server._request_certificate_from_ca(
                {"url": "https://ca.example.com", "token": "tok", "verify_ssl": True},
                cert_file,
                key_file,
            )
        assert result is True
        assert Path(cert_file).read_text() == "---CERT---"
        assert Path(key_file).read_text() == "---KEY---"

    def test_failed_request(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch("requests.post", return_value=mock_response):
            result = server._request_certificate_from_ca(
                {"url": "https://ca.example.com"},
                "/tmp/cert.crt",
                "/tmp/key.key",
            )
        assert result is False

    def test_request_exception(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        import requests as req_module

        with patch("requests.post", side_effect=req_module.ConnectionError("fail")):
            result = server._request_certificate_from_ca(
                {"url": "https://ca.example.com"},
                "/tmp/cert.crt",
                "/tmp/key.key",
            )
        assert result is False

    def test_no_token(self, tmp_path: Path) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        cert_file = str(tmp_path / "server.crt")
        key_file = str(tmp_path / "server.key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "certificate": "---CERT---",
            "private_key": "---KEY---",
        }

        with patch("requests.post", return_value=mock_response):
            result = server._request_certificate_from_ca(
                {"url": "https://ca.example.com"},
                cert_file,
                key_file,
            )
        assert result is True

    def test_response_missing_cert_data(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"certificate": None, "private_key": None}

        with patch("requests.post", return_value=mock_response):
            result = server._request_certificate_from_ca(
                {"url": "https://ca.example.com"},
                "/tmp/cert.crt",
                "/tmp/key.key",
            )
        assert result is False


@pytest.mark.unit
class TestServerStartStop:
    """Tests for start/stop methods."""

    def test_start_success(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        with patch.object(server.app, "run"):
            result = server.start()
        assert result is True
        assert server.running is True
        assert server.server_thread is not None

        # Clean up
        server.stop()

    def test_start_failure(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        with patch("threading.Thread", side_effect=RuntimeError("thread fail")):
            result = server.start()
        assert result is False
        assert server.running is False

    def test_stop_thread_alive_then_stops(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        server.running = True
        mock_thread = MagicMock()
        # is_alive returns True (triggers join), then False (clean stop)
        mock_thread.is_alive.side_effect = [True, False]
        server.server_thread = mock_thread

        server.stop()
        assert server.running is False
        assert server.server_thread is None
        mock_thread.join.assert_called_once_with(timeout=2.0)

    def test_stop_thread_still_alive_after_join(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        server.running = True
        mock_thread = MagicMock()
        # is_alive returns True both times (did not stop cleanly)
        mock_thread.is_alive.return_value = True
        server.server_thread = mock_thread

        server.stop()
        assert server.running is False
        assert server.server_thread is None

    def test_stop_thread_already_dead(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        server.running = True
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        server.server_thread = mock_thread

        server.stop()
        assert server.running is False
        assert server.server_thread is None
        mock_thread.join.assert_not_called()

    def test_stop_no_thread(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        server.running = True
        server.server_thread = None

        server.stop()
        assert server.running is False


@pytest.mark.unit
class TestServerRun:
    """Tests for the _run method."""

    def test_run_http(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        with patch.object(server.app, "run") as mock_run:
            server._run()

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["ssl_context"] is None

    def test_run_https(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        server.ssl_enabled = True
        mock_ctx = MagicMock(spec=ssl.SSLContext)
        server.ssl_context = mock_ctx

        with patch.object(server.app, "run") as mock_run:
            server._run()

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["ssl_context"] is mock_ctx

    def test_run_error_while_running(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        server.running = True

        with patch.object(server.app, "run", side_effect=OSError("addr in use")):
            # Should not raise - just log error
            server._run()

    def test_run_error_while_stopped(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)
        server.running = False

        with patch.object(server.app, "run", side_effect=OSError("addr in use")):
            # Should not raise or log (since not running)
            server._run()

    def test_run_with_debug(self) -> None:
        pbx_core = _make_pbx_core()
        server = PBXFlaskServer(pbx_core)

        with patch.dict("os.environ", {"FLASK_DEBUG": "1"}):
            with patch.object(server.app, "run") as mock_run:
                server._run()

        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["debug"] is True
        assert call_kwargs[1]["use_reloader"] is True
