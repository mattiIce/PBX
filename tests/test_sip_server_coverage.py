"""Comprehensive tests for pbx/sip/server.py - SIP protocol server."""

import socket
import threading
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

from pbx.sip.server import (
    RFC2833_EVENT_TO_DTMF,
    VALID_DTMF_DIGITS,
    SIPServer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request_message(
    method: str = "INVITE",
    *,
    from_header: str = "<sip:1001@pbx.local>",
    to_header: str = "<sip:1002@pbx.local>",
    call_id: str = "test-call-id-123",
    body: str = "",
    extra_headers: dict[str, str] | None = None,
) -> MagicMock:
    """Build a MagicMock that behaves like a SIPMessage request."""
    msg = MagicMock()
    msg.method = method
    msg.status_code = None
    msg.body = body
    msg.is_request.return_value = True
    msg.is_response.return_value = False
    msg.build.return_value = f"{method} sip:1002@pbx.local SIP/2.0\r\n\r\n"

    headers: dict[str, str] = {
        "From": from_header,
        "To": to_header,
        "Call-ID": call_id,
        "CSeq": "1 " + method,
    }
    if extra_headers:
        headers.update(extra_headers)

    msg.get_header.side_effect = headers.get
    return msg


def _make_response_message(
    status_code: int = 200,
    *,
    call_id: str = "test-call-id-123",
) -> MagicMock:
    """Build a MagicMock that behaves like a SIPMessage response."""
    msg = MagicMock()
    msg.method = None
    msg.status_code = status_code
    msg.is_request.return_value = False
    msg.is_response.return_value = True
    msg.build.return_value = f"SIP/2.0 {status_code} OK\r\n\r\n"

    headers: dict[str, str] = {
        "Call-ID": call_id,
    }
    msg.get_header.side_effect = headers.get
    return msg


ADDR = ("192.168.1.100", 5060)


# ===========================================================================
# Module-level constants
# ===========================================================================


@pytest.mark.unit
class TestModuleConstants:
    """Tests for module-level constants."""

    def test_valid_dtmf_digits_contains_all_expected(self) -> None:
        expected = list("0123456789*#ABCD")
        assert expected == VALID_DTMF_DIGITS

    def test_rfc2833_event_map_contains_star(self) -> None:
        assert RFC2833_EVENT_TO_DTMF["10"] == "*"

    def test_rfc2833_event_map_contains_hash(self) -> None:
        assert RFC2833_EVENT_TO_DTMF["11"] == "#"

    def test_rfc2833_event_map_digit_identity(self) -> None:
        for i in range(10):
            assert RFC2833_EVENT_TO_DTMF[str(i)] == str(i)

    def test_rfc2833_event_map_letters(self) -> None:
        assert RFC2833_EVENT_TO_DTMF["12"] == "A"
        assert RFC2833_EVENT_TO_DTMF["13"] == "B"
        assert RFC2833_EVENT_TO_DTMF["14"] == "C"
        assert RFC2833_EVENT_TO_DTMF["15"] == "D"


# ===========================================================================
# SIPServer.__init__
# ===========================================================================


@pytest.mark.unit
class TestSIPServerInit:
    """Tests for SIPServer initialization."""

    @patch("pbx.sip.server.get_logger")
    def test_default_values(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        assert server.host == "0.0.0.0"
        assert server.port == 5060
        assert server.pbx_core is None
        assert server.socket is None
        assert server.running is False

    @patch("pbx.sip.server.get_logger")
    def test_custom_values(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(host="10.0.0.1", port=5080, pbx_core=pbx)
        assert server.host == "10.0.0.1"
        assert server.port == 5080
        assert server.pbx_core is pbx


# ===========================================================================
# SIPServer.start / stop
# ===========================================================================


@pytest.mark.unit
class TestSIPServerStartStop:
    """Tests for start() and stop() methods."""

    @patch("pbx.sip.server.get_logger")
    @patch("socket.socket")
    @patch("threading.Thread")
    def test_start_success(
        self,
        mock_thread_cls: MagicMock,
        mock_socket_cls: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        server = SIPServer()
        result = server.start()

        assert result is True
        assert server.running is True
        mock_sock.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_sock.settimeout.assert_called_once_with(1.0)
        mock_sock.bind.assert_called_once_with(("0.0.0.0", 5060))
        mock_thread.start.assert_called_once()
        assert mock_thread.daemon is True

    @patch("pbx.sip.server.get_logger")
    @patch("socket.socket")
    def test_start_bind_failure(
        self,
        mock_socket_cls: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError("Address already in use")
        mock_socket_cls.return_value = mock_sock

        server = SIPServer()
        result = server.start()

        assert result is False
        assert server.running is False

    @patch("pbx.sip.server.get_logger")
    def test_stop_with_socket(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        mock_sock = MagicMock()
        server.socket = mock_sock
        server.running = True

        server.stop()

        assert server.running is False
        mock_sock.close.assert_called_once()

    @patch("pbx.sip.server.get_logger")
    def test_stop_without_socket(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server.running = True
        server.stop()
        assert server.running is False


# ===========================================================================
# SIPServer._listen
# ===========================================================================


@pytest.mark.unit
class TestSIPServerListen:
    """Tests for _listen() method."""

    @patch("pbx.sip.server.get_logger")
    @patch("threading.Thread")
    def test_listen_processes_message(
        self,
        mock_thread_cls: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        server = SIPServer()
        mock_sock = MagicMock()
        server.socket = mock_sock

        # First call returns data, second raises TimeoutError, third stops
        call_count = 0

        def recvfrom_side_effect(size: int) -> tuple[bytes, tuple[str, int]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (b"REGISTER sip:pbx.local SIP/2.0\r\n\r\n", ADDR)
            server.running = False
            raise TimeoutError

        mock_sock.recvfrom.side_effect = recvfrom_side_effect
        server.running = True

        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        server._listen()

        assert mock_thread_cls.called
        mock_thread.start.assert_called()

    @patch("pbx.sip.server.get_logger")
    def test_listen_timeout_continues(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        mock_sock = MagicMock()
        server.socket = mock_sock

        call_count = 0

        def recvfrom_side_effect(size: int) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                server.running = False
            raise TimeoutError

        mock_sock.recvfrom.side_effect = recvfrom_side_effect
        server.running = True

        server._listen()
        assert call_count >= 2

    @patch("pbx.sip.server.get_logger")
    def test_listen_oserror_while_running(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        mock_sock = MagicMock()
        server.socket = mock_sock

        call_count = 0

        def recvfrom_side_effect(size: int) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("socket error")
            server.running = False
            raise TimeoutError

        mock_sock.recvfrom.side_effect = recvfrom_side_effect
        server.running = True

        server._listen()
        # Should have logged error and continued
        logger = mock_get_logger.return_value
        logger.error.assert_called()

    @patch("pbx.sip.server.get_logger")
    def test_listen_oserror_while_not_running(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        mock_sock = MagicMock()
        server.socket = mock_sock

        def recvfrom_side_effect(size: int) -> None:
            server.running = False
            raise OSError("socket closed")

        mock_sock.recvfrom.side_effect = recvfrom_side_effect
        server.running = True

        server._listen()
        # Error should NOT be logged because running was False when exception hit
        logger = mock_get_logger.return_value
        logger.error.assert_not_called()


# ===========================================================================
# SIPServer._handle_message
# ===========================================================================


@pytest.mark.unit
class TestHandleMessage:
    """Tests for _handle_message()."""

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessage")
    def test_handle_request_dispatched(
        self,
        mock_sip_msg_cls: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        msg = MagicMock()
        msg.method = "REGISTER"
        msg.status_code = None
        msg.is_request.return_value = True
        msg.is_response.return_value = False
        mock_sip_msg_cls.return_value = msg

        server = SIPServer()
        server._handle_request = MagicMock()
        server._handle_response = MagicMock()

        server._handle_message("raw msg", ADDR)

        server._handle_request.assert_called_once_with(msg, ADDR)
        server._handle_response.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessage")
    def test_handle_response_dispatched(
        self,
        mock_sip_msg_cls: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        msg = MagicMock()
        msg.method = None
        msg.status_code = 200
        msg.is_request.return_value = False
        msg.is_response.return_value = True
        mock_sip_msg_cls.return_value = msg

        server = SIPServer()
        server._handle_request = MagicMock()
        server._handle_response = MagicMock()

        server._handle_message("raw msg", ADDR)

        server._handle_response.assert_called_once_with(msg, ADDR)
        server._handle_request.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessage")
    def test_handle_message_parse_error(
        self,
        mock_sip_msg_cls: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_sip_msg_cls.side_effect = Exception("parse error")

        server = SIPServer()
        server._handle_message("garbage", ADDR)

        logger = mock_get_logger.return_value
        logger.error.assert_called()


# ===========================================================================
# SIPServer._handle_request - dispatch to each method
# ===========================================================================


@pytest.mark.unit
class TestHandleRequest:
    """Tests for _handle_request() dispatch logic."""

    @patch("pbx.sip.server.get_logger")
    def _make_server(self, mock_get_logger: MagicMock) -> SIPServer:
        server = SIPServer()
        server._send_response = MagicMock()
        server._send_message = MagicMock()
        return server

    def test_dispatch_register(self) -> None:
        server = self._make_server()
        server._handle_register = MagicMock()
        msg = _make_request_message("REGISTER")
        server._handle_request(msg, ADDR)
        server._handle_register.assert_called_once_with(msg, ADDR)

    def test_dispatch_invite(self) -> None:
        server = self._make_server()
        server._handle_invite = MagicMock()
        msg = _make_request_message("INVITE")
        server._handle_request(msg, ADDR)
        server._handle_invite.assert_called_once_with(msg, ADDR)

    def test_dispatch_ack(self) -> None:
        server = self._make_server()
        server._handle_ack = MagicMock()
        msg = _make_request_message("ACK")
        server._handle_request(msg, ADDR)
        server._handle_ack.assert_called_once_with(msg, ADDR)

    def test_dispatch_bye(self) -> None:
        server = self._make_server()
        server._handle_bye = MagicMock()
        msg = _make_request_message("BYE")
        server._handle_request(msg, ADDR)
        server._handle_bye.assert_called_once_with(msg, ADDR)

    def test_dispatch_cancel(self) -> None:
        server = self._make_server()
        server._handle_cancel = MagicMock()
        msg = _make_request_message("CANCEL")
        server._handle_request(msg, ADDR)
        server._handle_cancel.assert_called_once_with(msg, ADDR)

    def test_dispatch_options(self) -> None:
        server = self._make_server()
        server._handle_options = MagicMock()
        msg = _make_request_message("OPTIONS")
        server._handle_request(msg, ADDR)
        server._handle_options.assert_called_once_with(msg, ADDR)

    def test_dispatch_subscribe(self) -> None:
        server = self._make_server()
        server._handle_subscribe = MagicMock()
        msg = _make_request_message("SUBSCRIBE")
        server._handle_request(msg, ADDR)
        server._handle_subscribe.assert_called_once_with(msg, ADDR)

    def test_dispatch_notify(self) -> None:
        server = self._make_server()
        server._handle_notify = MagicMock()
        msg = _make_request_message("NOTIFY")
        server._handle_request(msg, ADDR)
        server._handle_notify.assert_called_once_with(msg, ADDR)

    def test_dispatch_refer(self) -> None:
        server = self._make_server()
        server._handle_refer = MagicMock()
        msg = _make_request_message("REFER")
        server._handle_request(msg, ADDR)
        server._handle_refer.assert_called_once_with(msg, ADDR)

    def test_dispatch_info(self) -> None:
        server = self._make_server()
        server._handle_info = MagicMock()
        msg = _make_request_message("INFO")
        server._handle_request(msg, ADDR)
        server._handle_info.assert_called_once_with(msg, ADDR)

    def test_dispatch_message(self) -> None:
        server = self._make_server()
        server._handle_sip_message_method = MagicMock()
        msg = _make_request_message("MESSAGE")
        server._handle_request(msg, ADDR)
        server._handle_sip_message_method.assert_called_once_with(msg, ADDR)

    def test_dispatch_prack(self) -> None:
        server = self._make_server()
        server._handle_prack = MagicMock()
        msg = _make_request_message("PRACK")
        server._handle_request(msg, ADDR)
        server._handle_prack.assert_called_once_with(msg, ADDR)

    def test_dispatch_update(self) -> None:
        server = self._make_server()
        server._handle_update = MagicMock()
        msg = _make_request_message("UPDATE")
        server._handle_request(msg, ADDR)
        server._handle_update.assert_called_once_with(msg, ADDR)

    def test_dispatch_publish(self) -> None:
        server = self._make_server()
        server._handle_publish = MagicMock()
        msg = _make_request_message("PUBLISH")
        server._handle_request(msg, ADDR)
        server._handle_publish.assert_called_once_with(msg, ADDR)

    def test_dispatch_unknown_method_returns_405(self) -> None:
        server = self._make_server()
        msg = _make_request_message("FOOBAR")
        server._handle_request(msg, ADDR)
        server._send_response.assert_called_once_with(405, "Method Not Allowed", msg, ADDR)


# ===========================================================================
# SIPServer._handle_register
# ===========================================================================


@pytest.mark.unit
class TestHandleRegister:
    """Tests for _handle_register()."""

    @patch("pbx.sip.server.get_logger")
    def test_register_with_pbx_core_success(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        pbx.register_extension.return_value = True
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "REGISTER",
            extra_headers={"User-Agent": "Polycom/5.0", "Contact": "<sip:1001@10.0.0.1>"},
        )
        server._handle_register(msg, ADDR)

        pbx.register_extension.assert_called_once_with(
            "<sip:1001@pbx.local>", ADDR, "Polycom/5.0", "<sip:1001@10.0.0.1>"
        )
        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_register_with_pbx_core_failure(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        pbx.register_extension.return_value = False
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message("REGISTER")
        server._handle_register(msg, ADDR)

        server._send_response.assert_called_once_with(401, "Unauthorized", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_register_without_pbx_core(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("REGISTER")
        server._handle_register(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)


# ===========================================================================
# SIPServer._handle_invite
# ===========================================================================


@pytest.mark.unit
class TestHandleInvite:
    """Tests for _handle_invite()."""

    @patch("pbx.sip.server.get_logger")
    def test_invite_with_pbx_core_success(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        pbx.route_call.return_value = True
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message("INVITE")
        server._handle_invite(msg, ADDR)

        pbx.route_call.assert_called_once_with(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "test-call-id-123",
            msg,
            ADDR,
        )
        server._send_response.assert_called_once_with(100, "Trying", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_invite_with_pbx_core_failure(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        pbx.route_call.return_value = False
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message("INVITE")
        server._handle_invite(msg, ADDR)

        server._send_response.assert_called_once_with(404, "Not Found", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_invite_without_pbx_core(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("INVITE")
        server._handle_invite(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)


# ===========================================================================
# SIPServer._handle_ack
# ===========================================================================


@pytest.mark.unit
class TestHandleAck:
    """Tests for _handle_ack()."""

    @patch("pbx.sip.server.get_logger")
    def test_ack_with_pbx_core_forwards_to_callee(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        mock_call = MagicMock()
        mock_call.callee_addr = ("10.0.0.2", 5060)
        pbx.call_manager.get_call.return_value = mock_call

        server = SIPServer(pbx_core=pbx)
        server._send_message = MagicMock()

        msg = _make_request_message("ACK")
        server._handle_ack(msg, ADDR)

        pbx.call_manager.get_call.assert_called_once_with("test-call-id-123")
        server._send_message.assert_called_once_with(msg.build(), ("10.0.0.2", 5060))

    @patch("pbx.sip.server.get_logger")
    def test_ack_call_not_found(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        pbx.call_manager.get_call.return_value = None

        server = SIPServer(pbx_core=pbx)
        server._send_message = MagicMock()

        msg = _make_request_message("ACK")
        server._handle_ack(msg, ADDR)

        server._send_message.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    def test_ack_call_no_callee_addr(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        mock_call = MagicMock()
        mock_call.callee_addr = None
        pbx.call_manager.get_call.return_value = mock_call

        server = SIPServer(pbx_core=pbx)
        server._send_message = MagicMock()

        msg = _make_request_message("ACK")
        server._handle_ack(msg, ADDR)

        server._send_message.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    def test_ack_no_call_id(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_message = MagicMock()

        msg = _make_request_message("ACK", call_id="")
        # Patch get_header to return None for Call-ID
        msg.get_header.side_effect = lambda name: None if name == "Call-ID" else ""
        server._handle_ack(msg, ADDR)

        pbx.call_manager.get_call.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    def test_ack_without_pbx_core(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        msg = _make_request_message("ACK")
        # Should not raise
        server._handle_ack(msg, ADDR)


# ===========================================================================
# SIPServer._handle_bye
# ===========================================================================


@pytest.mark.unit
class TestHandleBye:
    """Tests for _handle_bye()."""

    @patch("pbx.sip.server.get_logger")
    def test_bye_from_caller_forwards_to_callee(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        mock_call = MagicMock()
        mock_call.caller_addr = ADDR
        mock_call.callee_addr = ("10.0.0.2", 5060)
        mock_call.state = "CONNECTED"
        pbx.call_manager.get_call.return_value = mock_call

        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()
        server._send_message = MagicMock()

        msg = _make_request_message("BYE")
        server._handle_bye(msg, ADDR)

        server._send_message.assert_called_once_with(msg.build(), ("10.0.0.2", 5060))
        pbx.end_call.assert_called_once_with("test-call-id-123")
        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_bye_from_callee_forwards_to_caller(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        callee_addr = ("10.0.0.2", 5060)
        mock_call = MagicMock()
        mock_call.caller_addr = ("10.0.0.1", 5060)
        mock_call.callee_addr = callee_addr
        mock_call.state = "CONNECTED"
        pbx.call_manager.get_call.return_value = mock_call

        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()
        server._send_message = MagicMock()

        msg = _make_request_message("BYE")
        server._handle_bye(msg, callee_addr)

        server._send_message.assert_called_once_with(msg.build(), ("10.0.0.1", 5060))

    @patch("pbx.sip.server.get_logger")
    def test_bye_call_not_found(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        pbx.call_manager.get_call.return_value = None

        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()
        server._send_message = MagicMock()

        msg = _make_request_message("BYE")
        server._handle_bye(msg, ADDR)

        pbx.end_call.assert_called_once_with("test-call-id-123")
        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)
        server._send_message.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    def test_bye_forward_exception(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        mock_call = MagicMock()
        mock_call.caller_addr = ADDR
        mock_call.callee_addr = ("10.0.0.2", 5060)
        mock_call.state = "CONNECTED"
        pbx.call_manager.get_call.return_value = mock_call

        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()
        server._send_message = MagicMock(side_effect=Exception("network error"))

        msg = _make_request_message("BYE")
        server._handle_bye(msg, ADDR)

        # Should still end call and send response despite forward error
        pbx.end_call.assert_called_once()
        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_bye_without_pbx_core(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("BYE")
        server._handle_bye(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_bye_voicemail_call_attributes(self, mock_get_logger: MagicMock) -> None:
        """Test BYE handling with voicemail access attributes on call."""
        pbx = MagicMock()
        mock_call = MagicMock()
        mock_call.voicemail_access = True
        mock_call.voicemail_extension = "1001"
        mock_call.caller_addr = ADDR
        mock_call.callee_addr = None
        mock_call.state = "CONNECTED"
        pbx.call_manager.get_call.return_value = mock_call

        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()
        server._send_message = MagicMock()

        msg = _make_request_message("BYE")
        server._handle_bye(msg, ADDR)

        pbx.end_call.assert_called_once()
        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)


# ===========================================================================
# SIPServer._handle_cancel
# ===========================================================================


@pytest.mark.unit
class TestHandleCancel:
    """Tests for _handle_cancel()."""

    @patch("pbx.sip.server.get_logger")
    def test_cancel_responds_200(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("CANCEL")
        server._handle_cancel(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)


# ===========================================================================
# SIPServer._handle_options
# ===========================================================================


@pytest.mark.unit
class TestHandleOptions:
    """Tests for _handle_options()."""

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessageBuilder")
    def test_options_responds_with_allow_header(
        self,
        mock_builder: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_builder.build_response.return_value = mock_response

        server = SIPServer()
        server._send_message = MagicMock()

        msg = _make_request_message("OPTIONS")
        server._handle_options(msg, ADDR)

        mock_builder.build_response.assert_called_once_with(200, "OK", msg)
        mock_response.set_header.assert_called_once()
        # Verify the Allow header content
        set_header_call = mock_response.set_header.call_args
        assert set_header_call[0][0] == "Allow"
        assert "INVITE" in set_header_call[0][1]
        assert "REGISTER" in set_header_call[0][1]
        assert "PUBLISH" in set_header_call[0][1]
        server._send_message.assert_called_once()


# ===========================================================================
# SIPServer._handle_subscribe
# ===========================================================================


@pytest.mark.unit
class TestHandleSubscribe:
    """Tests for _handle_subscribe()."""

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessageBuilder")
    def test_subscribe_with_event(
        self,
        mock_builder: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_builder.build_response.return_value = mock_response

        server = SIPServer()
        server._send_message = MagicMock()

        msg = _make_request_message(
            "SUBSCRIBE",
            extra_headers={"Event": "presence", "Expires": "600"},
        )
        server._handle_subscribe(msg, ADDR)

        mock_response.set_header.assert_called_once_with("Expires", "600")
        server._send_message.assert_called_once()

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessageBuilder")
    def test_subscribe_without_event_header(
        self,
        mock_builder: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_builder.build_response.return_value = mock_response

        server = SIPServer()
        server._send_message = MagicMock()

        msg = _make_request_message("SUBSCRIBE")
        server._handle_subscribe(msg, ADDR)

        # Default expires of 3600
        mock_response.set_header.assert_called_once_with("Expires", "3600")

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessageBuilder")
    def test_subscribe_no_expires_uses_default(
        self,
        mock_builder: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_builder.build_response.return_value = mock_response

        server = SIPServer()
        server._send_message = MagicMock()

        msg = _make_request_message(
            "SUBSCRIBE",
            extra_headers={"Event": "dialog"},
        )
        server._handle_subscribe(msg, ADDR)

        mock_response.set_header.assert_called_once_with("Expires", "3600")


# ===========================================================================
# SIPServer._handle_notify
# ===========================================================================


@pytest.mark.unit
class TestHandleNotify:
    """Tests for _handle_notify()."""

    @patch("pbx.sip.server.get_logger")
    def test_notify_responds_200(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("NOTIFY")
        server._handle_notify(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)


# ===========================================================================
# SIPServer._handle_refer
# ===========================================================================


@pytest.mark.unit
class TestHandleRefer:
    """Tests for _handle_refer()."""

    @patch("pbx.sip.server.get_logger")
    def test_refer_with_refer_to_header(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message(
            "REFER",
            extra_headers={"Refer-To": "<sip:1003@pbx.local>"},
        )
        server._handle_refer(msg, ADDR)

        server._send_response.assert_called_once_with(202, "Accepted", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_refer_missing_refer_to_header(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("REFER")
        server._handle_refer(msg, ADDR)

        server._send_response.assert_called_once_with(
            400, "Bad Request - Missing Refer-To", msg, ADDR
        )


# ===========================================================================
# SIPServer._handle_info (DTMF)
# ===========================================================================


@pytest.mark.unit
class TestHandleInfo:
    """Tests for _handle_info() - DTMF via SIP INFO."""

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_relay_valid_digit(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=5\nDuration=160",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        server._handle_info(msg, ADDR)

        pbx.handle_dtmf_info.assert_called_once_with("test-call-id-123", "5")
        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_relay_star(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=*",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        server._handle_info(msg, ADDR)

        pbx.handle_dtmf_info.assert_called_once_with("test-call-id-123", "*")

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_relay_hash(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=#",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        server._handle_info(msg, ADDR)

        pbx.handle_dtmf_info.assert_called_once_with("test-call-id-123", "#")

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_rfc2833_event_code(self, mock_get_logger: MagicMock) -> None:
        """Phone sends event code '11' which maps to '#'."""
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=11",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        server._handle_info(msg, ADDR)

        pbx.handle_dtmf_info.assert_called_once_with("test-call-id-123", "#")

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_rfc2833_event_code_star(self, mock_get_logger: MagicMock) -> None:
        """Event code '10' maps to '*'."""
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=10",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        server._handle_info(msg, ADDR)

        pbx.handle_dtmf_info.assert_called_once_with("test-call-id-123", "*")

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_invalid_digit(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=X",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        server._handle_info(msg, ADDR)

        pbx.handle_dtmf_info.assert_not_called()
        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_application_dtm_content_type(self, mock_get_logger: MagicMock) -> None:
        """Content type starts with 'application/dtm' (partial match)."""
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=3",
            extra_headers={"Content-type": "application/dtmf"},
        )
        server._handle_info(msg, ADDR)

        pbx.handle_dtmf_info.assert_called_once_with("test-call-id-123", "3")

    @patch("pbx.sip.server.get_logger")
    def test_info_no_body(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("INFO")
        server._handle_info(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_info_no_content_type(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("INFO", body="Signal=5")
        server._handle_info(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_info_non_dtmf_content_type(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="some text",
            extra_headers={"Content-type": "text/plain"},
        )
        server._handle_info(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_without_pbx_core(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=5",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        server._handle_info(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_info_dtmf_without_call_id(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=5",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        # Override call_id to None
        original_side_effect = msg.get_header.side_effect

        def get_header_no_callid(name: str) -> str | None:
            if name == "Call-ID":
                return None
            return original_side_effect(name)

        msg.get_header.side_effect = get_header_no_callid

        server._handle_info(msg, ADDR)

        # handle_dtmf_info should NOT be called when call_id is None
        pbx.handle_dtmf_info.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    def test_info_body_with_signal_no_equals_value(self, mock_get_logger: MagicMock) -> None:
        """Edge case: Signal= with no value after the equals sign."""
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "INFO",
            body="Signal=",
            extra_headers={"Content-type": "application/dtmf-relay"},
        )
        server._handle_info(msg, ADDR)

        # Empty string is not a valid DTMF digit
        pbx.handle_dtmf_info.assert_not_called()


# ===========================================================================
# SIPServer._handle_sip_message_method
# ===========================================================================


@pytest.mark.unit
class TestHandleSIPMessageMethod:
    """Tests for _handle_sip_message_method() (MESSAGE method)."""

    @patch("pbx.sip.server.get_logger")
    def test_message_with_body_and_pbx_core(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)
        server._send_response = MagicMock()

        msg = _make_request_message(
            "MESSAGE",
            body="Hello there!",
            extra_headers={"Content-type": "text/plain"},
        )
        server._handle_sip_message_method(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_message_with_body_no_pbx_core(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("MESSAGE", body="Hello")
        server._handle_sip_message_method(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_message_empty_body(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("MESSAGE")
        server._handle_sip_message_method(msg, ADDR)

        logger = mock_get_logger.return_value
        logger.warning.assert_called()
        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)


# ===========================================================================
# SIPServer._handle_prack
# ===========================================================================


@pytest.mark.unit
class TestHandlePrack:
    """Tests for _handle_prack()."""

    @patch("pbx.sip.server.get_logger")
    def test_prack_with_rack_header(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message(
            "PRACK",
            extra_headers={"RAck": "1 1 INVITE"},
        )
        server._handle_prack(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_prack_without_rack_header(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("PRACK")
        server._handle_prack(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)


# ===========================================================================
# SIPServer._handle_update
# ===========================================================================


@pytest.mark.unit
class TestHandleUpdate:
    """Tests for _handle_update()."""

    @patch("pbx.sip.server.get_logger")
    def test_update_with_sdp(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message(
            "UPDATE",
            body="v=0\r\no=- 0 0 IN IP4 10.0.0.1",
            extra_headers={"Content-type": "application/sdp"},
        )
        server._handle_update(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_update_without_sdp(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message("UPDATE")
        server._handle_update(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_update_with_non_sdp_content_type(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        server._send_response = MagicMock()

        msg = _make_request_message(
            "UPDATE",
            body="some body",
            extra_headers={"Content-type": "text/plain"},
        )
        server._handle_update(msg, ADDR)

        server._send_response.assert_called_once_with(200, "OK", msg, ADDR)


# ===========================================================================
# SIPServer._handle_publish
# ===========================================================================


@pytest.mark.unit
class TestHandlePublish:
    """Tests for _handle_publish()."""

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessageBuilder")
    def test_publish_with_event_and_body(
        self,
        mock_builder: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_builder.build_response.return_value = mock_response

        server = SIPServer()
        server._send_message = MagicMock()

        msg = _make_request_message(
            "PUBLISH",
            body="<presence>online</presence>",
            extra_headers={
                "Event": "presence",
                "Expires": "1800",
                "Content-type": "application/pidf+xml",
            },
        )
        server._handle_publish(msg, ADDR)

        mock_builder.build_response.assert_called_once_with(200, "OK", msg)
        # Should set Expires and SIP-ETag
        calls = mock_response.set_header.call_args_list
        header_names = [c[0][0] for c in calls]
        assert "Expires" in header_names
        assert "SIP-ETag" in header_names
        server._send_message.assert_called_once()

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessageBuilder")
    def test_publish_with_sip_if_match(
        self,
        mock_builder: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_builder.build_response.return_value = mock_response

        server = SIPServer()
        server._send_message = MagicMock()

        msg = _make_request_message(
            "PUBLISH",
            extra_headers={
                "Event": "presence",
                "SIP-If-Match": "some-etag-value",
            },
        )
        server._handle_publish(msg, ADDR)

        server._send_message.assert_called_once()

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessageBuilder")
    def test_publish_without_event(
        self,
        mock_builder: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_builder.build_response.return_value = mock_response

        server = SIPServer()
        server._send_message = MagicMock()

        msg = _make_request_message("PUBLISH")
        server._handle_publish(msg, ADDR)

        # Default expires 3600
        calls = mock_response.set_header.call_args_list
        expires_call = [c for c in calls if c[0][0] == "Expires"]
        assert len(expires_call) == 1
        assert expires_call[0][0][1] == "3600"


# ===========================================================================
# SIPServer._handle_response
# ===========================================================================


@pytest.mark.unit
class TestHandleResponse:
    """Tests for _handle_response()."""

    @patch("pbx.sip.server.get_logger")
    def test_response_180_ringing_forwards_to_caller(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        mock_call = MagicMock()
        mock_call.caller_addr = ("10.0.0.1", 5060)
        pbx.call_manager.get_call.return_value = mock_call

        server = SIPServer(pbx_core=pbx)
        server._send_message = MagicMock()

        msg = _make_response_message(180)
        server._handle_response(msg, ADDR)

        mock_call.ring.assert_called_once()
        server._send_message.assert_called_once_with(msg.build(), ("10.0.0.1", 5060))

    @patch("pbx.sip.server.get_logger")
    def test_response_180_no_caller_addr(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        mock_call = MagicMock()
        mock_call.caller_addr = None
        pbx.call_manager.get_call.return_value = mock_call

        server = SIPServer(pbx_core=pbx)
        server._send_message = MagicMock()

        msg = _make_response_message(180)
        server._handle_response(msg, ADDR)

        mock_call.ring.assert_called_once()
        server._send_message.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    def test_response_180_call_not_found(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        pbx.call_manager.get_call.return_value = None

        server = SIPServer(pbx_core=pbx)
        server._send_message = MagicMock()

        msg = _make_response_message(180)
        server._handle_response(msg, ADDR)

        server._send_message.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    def test_response_200_callee_answered(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)

        msg = _make_response_message(200)
        server._handle_response(msg, ADDR)

        pbx.handle_callee_answer.assert_called_once_with("test-call-id-123", msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_response_200_no_call_id(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)

        msg = _make_response_message(200)
        msg.get_header.side_effect = lambda name: None
        server._handle_response(msg, ADDR)

        pbx.handle_callee_answer.assert_not_called()

    @patch("pbx.sip.server.get_logger")
    def test_response_without_pbx_core(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        msg = _make_response_message(200)
        # Should not raise
        server._handle_response(msg, ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_response_other_status_code(self, mock_get_logger: MagicMock) -> None:
        pbx = MagicMock()
        server = SIPServer(pbx_core=pbx)

        msg = _make_response_message(486)
        server._handle_response(msg, ADDR)

        # No specific handling for 486, just logs
        pbx.handle_callee_answer.assert_not_called()


# ===========================================================================
# SIPServer._send_response / _send_message
# ===========================================================================


@pytest.mark.unit
class TestSendMethods:
    """Tests for _send_response() and _send_message()."""

    @patch("pbx.sip.server.get_logger")
    @patch("pbx.sip.server.SIPMessageBuilder")
    def test_send_response_builds_and_sends(
        self,
        mock_builder: MagicMock,
        mock_get_logger: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_response.build.return_value = "SIP/2.0 200 OK\r\n\r\n"
        mock_builder.build_response.return_value = mock_response

        server = SIPServer()
        server._send_message = MagicMock()

        req = _make_request_message("REGISTER")
        server._send_response(200, "OK", req, ADDR)

        mock_builder.build_response.assert_called_once_with(200, "OK", req)
        server._send_message.assert_called_once_with("SIP/2.0 200 OK\r\n\r\n", ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_send_message_success(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        mock_sock = MagicMock()
        server.socket = mock_sock

        server._send_message("SIP/2.0 200 OK\r\n\r\n", ADDR)

        mock_sock.sendto.assert_called_once_with(b"SIP/2.0 200 OK\r\n\r\n", ADDR)

    @patch("pbx.sip.server.get_logger")
    def test_send_message_oserror(self, mock_get_logger: MagicMock) -> None:
        server = SIPServer()
        mock_sock = MagicMock()
        mock_sock.sendto.side_effect = OSError("send failed")
        server.socket = mock_sock

        server._send_message("SIP/2.0 200 OK\r\n\r\n", ADDR)

        logger = mock_get_logger.return_value
        logger.error.assert_called()
