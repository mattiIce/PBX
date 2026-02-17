"""Comprehensive tests for pbx/rtp/handler.py"""

from __future__ import annotations

import struct
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, mock_open, patch

import pytest


# ---------------------------------------------------------------------------
# RTPHandler tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRTPHandlerInit:
    """Tests for RTPHandler.__init__."""

    def test_init_defaults(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)
        assert h.local_port == 5000
        assert h.remote_host is None
        assert h.remote_port is None
        assert h.socket is None
        assert h.running is False
        assert h.sequence_number == 0
        assert h.timestamp == 0
        assert h.ssrc == 0x12345678

    def test_init_with_remote(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000, remote_host="10.0.0.1", remote_port=6000)
        assert h.remote_host == "10.0.0.1"
        assert h.remote_port == 6000


@pytest.mark.unit
class TestRTPHandlerStart:
    """Tests for RTPHandler.start."""

    def test_start_success(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        mock_sock = MagicMock()
        with (
            patch("pbx.rtp.handler.socket.socket", return_value=mock_sock),
            patch("pbx.rtp.handler.threading.Thread") as mock_thread_cls,
        ):
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            result = h.start()

        assert result is True
        assert h.running is True
        assert h.socket is mock_sock
        mock_sock.setsockopt.assert_called_once()
        mock_sock.bind.assert_called_once_with(("0.0.0.0", 5000))
        mock_thread.start.assert_called_once()

    def test_start_failure_oserror(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        with patch("pbx.rtp.handler.socket.socket", side_effect=OSError("bind failed")):
            result = h.start()

        assert result is False


@pytest.mark.unit
class TestRTPHandlerStop:
    """Tests for RTPHandler.stop."""

    def test_stop_with_socket(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h.stop()
        assert h.running is False
        mock_sock.close.assert_called_once()

    def test_stop_without_socket(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        h.running = True
        h.stop()
        assert h.running is False


@pytest.mark.unit
class TestRTPHandlerReceiveLoop:
    """Tests for RTPHandler._receive_loop."""

    def test_receive_loop_processes_packet(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        # Build a valid 12-byte RTP header + payload
        rtp_header = struct.pack("!BBHII", 0x80, 0, 1, 160, 0x12345678)
        payload = b"\x00" * 20
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h.socket = mock_sock
        h.running = True
        h._receive_loop()

    def test_receive_loop_oserror_while_running(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                h.running = False
            raise OSError("net error")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h.socket = mock_sock
        h.running = True
        h._receive_loop()

    def test_receive_loop_oserror_while_not_running(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        mock_sock = MagicMock()

        def recv_side_effect(size):
            h.running = False
            raise OSError("closed")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h.socket = mock_sock
        h.running = True
        h._receive_loop()


@pytest.mark.unit
class TestRTPHandlerHandleRTPPacket:
    """Tests for RTPHandler._handle_rtp_packet."""

    def test_short_packet_ignored(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        # Should return without error for short packet
        h._handle_rtp_packet(b"\x00" * 11, ("10.0.0.1", 6000))

    def test_valid_packet_parsed(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        rtp_header = struct.pack("!BBHII", 0x80, 0, 42, 1000, 0xDEADBEEF)
        payload = b"\xFF" * 160
        h._handle_rtp_packet(rtp_header + payload, ("10.0.0.1", 6000))


@pytest.mark.unit
class TestRTPHandlerSendPacket:
    """Tests for RTPHandler.send_packet."""

    def test_send_no_remote_host(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000)

        assert h.send_packet(b"\x00" * 160) is False

    def test_send_no_remote_port(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000, remote_host="10.0.0.1")

        assert h.send_packet(b"\x00" * 160) is False

    def test_send_success(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        h.socket = mock_sock

        assert h.send_packet(b"\x00" * 160, payload_type=0, marker=True) is True
        mock_sock.sendto.assert_called_once()
        assert h.sequence_number == 1
        assert h.timestamp == 160

    def test_send_wraps_sequence_number(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        h.socket = mock_sock
        h.sequence_number = 0xFFFF

        h.send_packet(b"\x00" * 10)
        assert h.sequence_number == 0

    def test_send_oserror(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        mock_sock.sendto.side_effect = OSError("send failed")
        h.socket = mock_sock

        assert h.send_packet(b"\x00" * 10) is False

    def test_send_marker_false(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPHandler

            h = RTPHandler(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        h.socket = mock_sock

        h.send_packet(b"\x00" * 10, payload_type=8, marker=False)
        sent_data = mock_sock.sendto.call_args[0][0]
        byte1 = sent_data[1]
        assert (byte1 >> 7) == 0  # marker bit not set


# ---------------------------------------------------------------------------
# RTPRelay tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRTPRelayInit:
    """Tests for RTPRelay.__init__."""

    def test_init_defaults(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay()
        assert r.port_range_start == 10000
        assert r.port_range_end == 20000
        assert r.active_relays == {}
        assert r.qos_monitor is None
        assert len(r.port_pool) > 0

    def test_init_custom_range(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay(port_range_start=30000, port_range_end=30010)
        assert r.port_pool == [30000, 30002, 30004, 30006, 30008]


@pytest.mark.unit
class TestRTPRelayAllocate:
    """Tests for RTPRelay.allocate_relay."""

    def test_allocate_success(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay(port_range_start=30000, port_range_end=30004)

        with patch("pbx.rtp.handler.RTPRelayHandler") as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.start.return_value = True
            mock_handler_cls.return_value = mock_handler

            result = r.allocate_relay("call-1")

        assert result == (30000, 30001)
        assert "call-1" in r.active_relays
        assert r.active_relays["call-1"]["rtp_port"] == 30000

    def test_allocate_no_ports(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay(port_range_start=30000, port_range_end=30002)

        r.port_pool = []
        result = r.allocate_relay("call-1")
        assert result is None

    def test_allocate_handler_start_fails(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay(port_range_start=30000, port_range_end=30004)

        original_pool = r.port_pool.copy()
        with patch("pbx.rtp.handler.RTPRelayHandler") as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.start.return_value = False
            mock_handler_cls.return_value = mock_handler

            result = r.allocate_relay("call-1")

        assert result is None
        # Port should be returned to pool
        assert 30000 in r.port_pool


@pytest.mark.unit
class TestRTPRelaySetEndpoints:
    """Tests for RTPRelay.set_endpoints."""

    def test_set_endpoints_existing_call(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay()

        mock_handler = MagicMock()
        r.active_relays["call-1"] = {"handler": mock_handler, "rtp_port": 10000, "rtcp_port": 10001}

        ep_a = ("10.0.0.1", 5000)
        ep_b = ("10.0.0.2", 6000)
        r.set_endpoints("call-1", ep_a, ep_b)

        mock_handler.set_endpoints.assert_called_once_with(ep_a, ep_b)

    def test_set_endpoints_nonexistent_call(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay()

        # Should not raise
        r.set_endpoints("no-such-call", ("10.0.0.1", 5000), ("10.0.0.2", 6000))


@pytest.mark.unit
class TestRTPRelayRelease:
    """Tests for RTPRelay.release_relay."""

    def test_release_existing(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay(port_range_start=30000, port_range_end=30010)

        mock_handler = MagicMock()
        r.active_relays["call-1"] = {"handler": mock_handler, "rtp_port": 30000, "rtcp_port": 30001}
        # Remove 30000 from pool (as if it was allocated)
        if 30000 in r.port_pool:
            r.port_pool.remove(30000)

        r.release_relay("call-1")

        mock_handler.stop.assert_called_once()
        assert "call-1" not in r.active_relays
        assert 30000 in r.port_pool

    def test_release_nonexistent(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelay

            r = RTPRelay()

        # Should not raise
        r.release_relay("no-such-call")


# ---------------------------------------------------------------------------
# RTPRelayHandler tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRTPRelayHandlerInit:
    """Tests for RTPRelayHandler.__init__."""

    def test_init_no_qos(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="call-1")
        assert h.local_port == 10000
        assert h.call_id == "call-1"
        assert h.running is False
        assert h.endpoint_a is None
        assert h.endpoint_b is None
        assert h.learned_a is None
        assert h.learned_b is None
        assert h.qos_monitor is None
        assert h.qos_metrics_a_to_b is None
        assert h.qos_metrics_b_to_a is None

    def test_init_with_qos(self) -> None:
        mock_qos = MagicMock()
        mock_metrics_ab = MagicMock()
        mock_metrics_ba = MagicMock()
        mock_qos.start_monitoring.side_effect = [mock_metrics_ab, mock_metrics_ba]

        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="call-1", qos_monitor=mock_qos)

        assert h.qos_monitor is mock_qos
        assert h.qos_metrics_a_to_b is mock_metrics_ab
        assert h.qos_metrics_b_to_a is mock_metrics_ba
        mock_qos.start_monitoring.assert_any_call("call-1_a_to_b")
        mock_qos.start_monitoring.assert_any_call("call-1_b_to_a")


@pytest.mark.unit
class TestRTPRelayHandlerSetEndpoints:
    """Tests for RTPRelayHandler.set_endpoints."""

    def test_set_both(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        h.set_endpoints(("10.0.0.1", 5000), ("10.0.0.2", 6000))
        assert h.endpoint_a == ("10.0.0.1", 5000)
        assert h.endpoint_b == ("10.0.0.2", 6000)

    def test_set_only_a(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        h.set_endpoints(("10.0.0.1", 5000), None)
        assert h.endpoint_a == ("10.0.0.1", 5000)
        assert h.endpoint_b is None

    def test_set_preserves_existing(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        h.set_endpoints(("10.0.0.1", 5000), ("10.0.0.2", 6000))
        h.set_endpoints(None, ("10.0.0.3", 7000))
        assert h.endpoint_a == ("10.0.0.1", 5000)
        assert h.endpoint_b == ("10.0.0.3", 7000)


@pytest.mark.unit
class TestRTPRelayHandlerStart:
    """Tests for RTPRelayHandler.start."""

    def test_start_success(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        mock_sock = MagicMock()
        with (
            patch("pbx.rtp.handler.socket.socket", return_value=mock_sock),
            patch("pbx.rtp.handler.threading.Thread") as mock_thread_cls,
        ):
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            result = h.start()

        assert result is True
        assert h.running is True
        assert h._start_time is not None
        mock_thread.start.assert_called_once()

    def test_start_failure(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        with patch("pbx.rtp.handler.socket.socket", side_effect=OSError("fail")):
            result = h.start()

        assert result is False


@pytest.mark.unit
class TestRTPRelayHandlerStop:
    """Tests for RTPRelayHandler.stop."""

    def test_stop_with_socket_no_qos(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h.stop()
        assert h.running is False
        mock_sock.close.assert_called_once()

    def test_stop_with_qos(self) -> None:
        mock_qos = MagicMock()
        mock_qos.start_monitoring.side_effect = [MagicMock(), MagicMock()]
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1", qos_monitor=mock_qos)

        h.socket = MagicMock()
        h.running = True
        h.stop()
        mock_qos.stop_monitoring.assert_any_call("c1_a_to_b")
        mock_qos.stop_monitoring.assert_any_call("c1_b_to_a")

    def test_stop_no_socket(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        h.running = True
        h.stop()
        assert h.running is False


@pytest.mark.unit
class TestRTPRelayHandlerRelayLoop:
    """Tests for RTPRelayHandler._relay_loop."""

    @staticmethod
    def _make_rtp_packet(seq: int = 1, ts: int = 160, ssrc: int = 0xAABBCCDD) -> bytes:
        header = struct.pack("!BBHII", 0x80, 0, seq, ts, ssrc)
        return header + b"\x00" * 160

    def test_relay_from_a_to_b_learned(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.endpoint_a = ("10.0.0.1", 5000)
        h.endpoint_b = ("10.0.0.2", 6000)
        h.learned_a = ("10.0.0.1", 5000)
        h.learned_b = ("10.0.0.2", 6000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 5000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_sock.sendto.assert_called_with(packet, ("10.0.0.2", 6000))

    def test_relay_from_b_to_a_learned(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.endpoint_a = ("10.0.0.1", 5000)
        h.endpoint_b = ("10.0.0.2", 6000)
        h.learned_a = ("10.0.0.1", 5000)
        h.learned_b = ("10.0.0.2", 6000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.2", 6000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_sock.sendto.assert_called_with(packet, ("10.0.0.1", 5000))

    def test_relay_learns_endpoint_a_from_sdp(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.endpoint_a = ("10.0.0.1", 5000)
        h.endpoint_b = ("10.0.0.2", 6000)
        h.learned_b = ("10.0.0.2", 6000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 5000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        assert h.learned_a == ("10.0.0.1", 5000)
        mock_sock.sendto.assert_called_with(packet, ("10.0.0.2", 6000))

    def test_relay_learns_endpoint_b_from_sdp(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.endpoint_a = ("10.0.0.1", 5000)
        h.endpoint_b = ("10.0.0.2", 6000)
        h.learned_a = ("10.0.0.1", 5000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.2", 6000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        assert h.learned_b == ("10.0.0.2", 6000)
        mock_sock.sendto.assert_called_with(packet, ("10.0.0.1", 5000))

    def test_relay_symmetric_rtp_learn_a(self) -> None:
        """Learn endpoint A from first unknown packet (NAT traversal)."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        # No endpoints set at all

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("192.168.1.50", 9000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        assert h.learned_a == ("192.168.1.50", 9000)

    def test_relay_symmetric_rtp_learn_b(self) -> None:
        """Learn endpoint B from second unknown packet (NAT traversal)."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.learned_a = ("192.168.1.50", 9000)
        # No B learned

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("192.168.1.51", 9001))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        assert h.learned_b == ("192.168.1.51", 9001)

    def test_relay_learning_timeout_expired_a(self) -> None:
        """Reject packet from unknown source after learning timeout (for A)."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time() - 20.0  # Well past timeout

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("192.168.1.50", 9000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        assert h.learned_a is None
        mock_sock.sendto.assert_not_called()

    def test_relay_learning_timeout_expired_b(self) -> None:
        """Reject packet from unknown source after learning timeout (for B)."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time() - 20.0
        h.learned_a = ("192.168.1.50", 9000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("192.168.1.51", 9001))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        assert h.learned_b is None

    def test_relay_short_packet_rejected_learn_a(self) -> None:
        """Reject too-short packet during learning (A)."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        short_packet = b"\x00" * 5  # Too short
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (short_packet, ("192.168.1.50", 9000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        assert h.learned_a is None

    def test_relay_short_packet_rejected_learn_b(self) -> None:
        """Reject too-short packet during learning (B)."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        short_packet = b"\x00" * 5
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.learned_a = ("192.168.1.50", 9000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (short_packet, ("192.168.1.51", 9001))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        assert h.learned_b is None

    def test_relay_unknown_third_source(self) -> None:
        """Packet from unknown third source is dropped."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.learned_a = ("10.0.0.1", 5000)
        h.learned_b = ("10.0.0.2", 6000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.99", 9999))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_sock.sendto.assert_not_called()

    def test_relay_from_a_b_not_learned_use_sdp(self) -> None:
        """From A but B not learned - use SDP endpoint_b."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.endpoint_a = ("10.0.0.1", 5000)
        h.endpoint_b = ("10.0.0.2", 6000)
        h.learned_a = ("10.0.0.1", 5000)
        # learned_b is None

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 5000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_sock.sendto.assert_called_with(packet, ("10.0.0.2", 6000))

    def test_relay_from_b_a_not_learned_use_sdp(self) -> None:
        """From B but A not learned - use SDP endpoint_a."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.endpoint_a = ("10.0.0.1", 5000)
        h.endpoint_b = ("10.0.0.2", 6000)
        h.learned_b = ("10.0.0.2", 6000)
        # learned_a is None

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.2", 6000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_sock.sendto.assert_called_with(packet, ("10.0.0.1", 5000))

    def test_relay_from_a_no_b_at_all(self) -> None:
        """From A but no B known at all - packet dropped."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.endpoint_a = ("10.0.0.1", 5000)
        h.learned_a = ("10.0.0.1", 5000)
        # No endpoint_b or learned_b

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 5000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_sock.sendto.assert_not_called()

    def test_relay_from_b_no_a_at_all(self) -> None:
        """From B but no A known at all - packet dropped."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        packet = self._make_rtp_packet()
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.endpoint_b = ("10.0.0.2", 6000)
        h.learned_b = ("10.0.0.2", 6000)
        # No endpoint_a or learned_a

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.2", 6000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_sock.sendto.assert_not_called()

    def test_relay_qos_tracking_a_to_b(self) -> None:
        """QoS metrics updated for A->B forwarding."""
        mock_qos = MagicMock()
        mock_metrics_ab = MagicMock()
        mock_metrics_ba = MagicMock()
        mock_qos.start_monitoring.side_effect = [mock_metrics_ab, mock_metrics_ba]

        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1", qos_monitor=mock_qos)

        packet = self._make_rtp_packet(seq=42, ts=320)
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.learned_a = ("10.0.0.1", 5000)
        h.learned_b = ("10.0.0.2", 6000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 5000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_metrics_ab.update_packet_received.assert_called_once_with(42, 320, 160)
        mock_metrics_ab.update_packet_sent.assert_called_once()

    def test_relay_qos_tracking_b_to_a(self) -> None:
        """QoS metrics updated for B->A forwarding."""
        mock_qos = MagicMock()
        mock_metrics_ab = MagicMock()
        mock_metrics_ba = MagicMock()
        mock_qos.start_monitoring.side_effect = [mock_metrics_ab, mock_metrics_ba]

        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1", qos_monitor=mock_qos)

        packet = self._make_rtp_packet(seq=99, ts=640)
        mock_sock = MagicMock()
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h.learned_a = ("10.0.0.1", 5000)
        h.learned_b = ("10.0.0.2", 6000)

        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.2", 6000))
            h.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h._relay_loop()
        mock_metrics_ba.update_packet_received.assert_called_once_with(99, 640, 160)
        mock_metrics_ba.update_packet_sent.assert_called_once()

    def test_relay_loop_oserror(self) -> None:
        """OSError in relay loop is logged when running."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRelayHandler

            h = RTPRelayHandler(local_port=10000, call_id="c1")

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                h.running = False
            raise OSError("net error")

        mock_sock.recvfrom.side_effect = recv_side_effect
        h.socket = mock_sock
        h.running = True
        h._start_time = time.time()
        h._relay_loop()


# ---------------------------------------------------------------------------
# RTPRecorder tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRTPRecorderInit:
    """Tests for RTPRecorder.__init__."""

    def test_init(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")
        assert r.local_port == 5000
        assert r.call_id == "call-1"
        assert r.running is False
        assert r.recorded_data == []
        assert r.remote_endpoint is None
        assert r.rfc2833_handler is None

    def test_init_with_rfc2833(self) -> None:
        mock_handler = MagicMock()
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1", rfc2833_handler=mock_handler)
        assert r.rfc2833_handler is mock_handler


@pytest.mark.unit
class TestRTPRecorderStart:
    """Tests for RTPRecorder.start."""

    def test_start_success(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        mock_sock = MagicMock()
        with (
            patch("pbx.rtp.handler.socket.socket", return_value=mock_sock),
            patch("pbx.rtp.handler.threading.Thread") as mock_thread_cls,
        ):
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            result = r.start()

        assert result is True
        assert r.running is True
        mock_sock.settimeout.assert_called_once_with(0.5)

    def test_start_failure(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        with patch("pbx.rtp.handler.socket.socket", side_effect=OSError("fail")):
            result = r.start()

        assert result is False


@pytest.mark.unit
class TestRTPRecorderStop:
    """Tests for RTPRecorder.stop."""

    def test_stop_with_socket(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        mock_sock = MagicMock()
        r.socket = mock_sock
        r.running = True
        r.stop()
        assert r.running is False
        mock_sock.close.assert_called_once()

    def test_stop_socket_close_oserror(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("close error")
        r.socket = mock_sock
        r.running = True
        r.stop()  # Should not raise
        assert r.running is False

    def test_stop_no_socket(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        r.running = True
        r.stop()
        assert r.running is False


@pytest.mark.unit
class TestRTPRecorderRecordLoop:
    """Tests for RTPRecorder._record_loop."""

    def test_record_audio_payload(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        # PCMU packet (payload_type=0)
        rtp_header = struct.pack("!BBHII", 0x80, 0, 1, 160, 0xDEADBEEF)
        payload = b"\x7F" * 160
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            r.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        r.socket = mock_sock
        r.running = True
        r._record_loop()
        assert r.remote_endpoint == ("10.0.0.1", 6000)
        assert len(r.recorded_data) == 1
        assert r.recorded_data[0] == payload

    def test_record_filters_rfc2833(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        # RFC 2833 telephone-event (payload_type=101)
        rtp_header = struct.pack("!BBHII", 0x80, 101, 1, 160, 0xDEADBEEF)
        payload = b"\x00" * 4
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            r.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        r.socket = mock_sock
        r.running = True
        r._record_loop()
        assert len(r.recorded_data) == 0

    def test_record_rfc2833_with_handler(self) -> None:
        mock_rfc_handler = MagicMock()
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1", rfc2833_handler=mock_rfc_handler)

        rtp_header = struct.pack("!BBHII", 0x80, 101, 1, 160, 0xDEADBEEF)
        payload = b"\x00" * 4
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            r.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        r.socket = mock_sock
        r.running = True
        r._record_loop()
        mock_rfc_handler.handle_rtp_packet.assert_called_once_with(packet, ("10.0.0.1", 6000))

    def test_record_short_packet_ignored(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (b"\x00" * 5, ("10.0.0.1", 6000))
            r.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        r.socket = mock_sock
        r.running = True
        r._record_loop()
        assert len(r.recorded_data) == 0

    def test_record_timeout(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("timeout")
            r.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        r.socket = mock_sock
        r.running = True
        r._record_loop()

    def test_record_oserror_while_running(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                r.running = False
            raise OSError("error")

        mock_sock.recvfrom.side_effect = recv_side_effect
        r.socket = mock_sock
        r.running = True
        r._record_loop()


@pytest.mark.unit
class TestRTPRecorderGetAudio:
    """Tests for RTPRecorder.get_recorded_audio."""

    def test_empty(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")
        assert r.get_recorded_audio() == b""

    def test_combined(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")
        r.recorded_data = [b"\x01\x02", b"\x03\x04"]
        assert r.get_recorded_audio() == b"\x01\x02\x03\x04"


@pytest.mark.unit
class TestRTPRecorderGetDuration:
    """Tests for RTPRecorder.get_duration."""

    def test_no_packets(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")
        assert r.get_duration() == 0

    def test_50_packets(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")
        r.recorded_data = [b"\x00"] * 50
        # 50 packets * 20ms = 1000ms = 1 second
        assert r.get_duration() == 1

    def test_49_packets(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPRecorder

            r = RTPRecorder(local_port=5000, call_id="call-1")
        r.recorded_data = [b"\x00"] * 49
        # 49 * 20ms = 980ms -> 0 seconds (integer division)
        assert r.get_duration() == 0


# ---------------------------------------------------------------------------
# RTPPlayer tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRTPPlayerInit:
    """Tests for RTPPlayer.__init__."""

    def test_init_defaults(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)
        assert p.local_port == 5000
        assert p.remote_host == "10.0.0.1"
        assert p.remote_port == 6000
        assert p.call_id == "unknown"
        assert p.ssrc == 0x87654321

    def test_init_with_call_id(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000, call_id="c1")
        assert p.call_id == "c1"


@pytest.mark.unit
class TestRTPPlayerStart:
    """Tests for RTPPlayer.start."""

    def test_start_success(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        with patch("pbx.rtp.handler.socket.socket", return_value=mock_sock):
            result = p.start()

        assert result is True
        assert p.running is True

    def test_start_failure(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        with patch("pbx.rtp.handler.socket.socket", side_effect=OSError("fail")):
            result = p.start()

        assert result is False


@pytest.mark.unit
class TestRTPPlayerStop:
    """Tests for RTPPlayer.stop."""

    def test_stop_with_socket(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        p.socket = mock_sock
        p.running = True
        p.stop()
        assert p.running is False
        assert p.socket is None
        mock_sock.close.assert_called_once()

    def test_stop_socket_close_oserror(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("close fail")
        p.socket = mock_sock
        p.running = True
        p.stop()  # Should not raise (contextlib.suppress)
        assert p.running is False
        assert p.socket is None

    def test_stop_no_socket(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        p.running = True
        p.stop()
        assert p.running is False


@pytest.mark.unit
class TestRTPPlayerSendAudio:
    """Tests for RTPPlayer.send_audio."""

    def test_send_not_running(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        p.running = False
        assert p.send_audio(b"\x00" * 160) is False

    def test_send_no_socket(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        p.running = True
        p.socket = None
        assert p.send_audio(b"\x00" * 160) is False

    def test_send_pcmu_auto_bytes_per_sample(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        p.socket = mock_sock
        p.running = True

        # 160 bytes = 1 packet at payload_type=0 (1 byte/sample, 160 samples/packet)
        with patch("pbx.rtp.handler.time.sleep"):
            result = p.send_audio(b"\x00" * 160, payload_type=0)

        assert result is True
        assert mock_sock.sendto.call_count == 1

    def test_send_pcma_auto_bytes_per_sample(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        p.socket = mock_sock
        p.running = True

        with patch("pbx.rtp.handler.time.sleep"):
            result = p.send_audio(b"\x00" * 160, payload_type=8)

        assert result is True

    def test_send_g722_auto_bytes_per_sample(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        p.socket = mock_sock
        p.running = True

        with patch("pbx.rtp.handler.time.sleep"):
            result = p.send_audio(b"\x00" * 160, payload_type=9)

        assert result is True

    def test_send_pcm_auto_bytes_per_sample(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        p.socket = mock_sock
        p.running = True

        # payload_type=10 (PCM) -> 2 bytes/sample, 320 bytes/packet
        with patch("pbx.rtp.handler.time.sleep"):
            result = p.send_audio(b"\x00" * 320, payload_type=10)

        assert result is True
        assert mock_sock.sendto.call_count == 1

    def test_send_explicit_bytes_per_sample(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        p.socket = mock_sock
        p.running = True

        with patch("pbx.rtp.handler.time.sleep"):
            result = p.send_audio(b"\x00" * 160, payload_type=0, bytes_per_sample=1)

        assert result is True

    def test_send_multiple_packets(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        p.socket = mock_sock
        p.running = True

        # 320 bytes / 160 bytes per packet = 2 packets
        with patch("pbx.rtp.handler.time.sleep"):
            result = p.send_audio(b"\x00" * 320, payload_type=0)

        assert result is True
        assert mock_sock.sendto.call_count == 2
        # Check sequence wrapping
        assert p.sequence_number == 2

    def test_send_oserror(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        mock_sock = MagicMock()
        mock_sock.sendto.side_effect = OSError("send fail")
        p.socket = mock_sock
        p.running = True

        with patch("pbx.rtp.handler.time.sleep"):
            result = p.send_audio(b"\x00" * 160, payload_type=0)

        assert result is False


@pytest.mark.unit
class TestRTPPlayerBuildRTPPacket:
    """Tests for RTPPlayer._build_rtp_packet."""

    def test_builds_correct_header(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        p.sequence_number = 100
        p.timestamp = 16000
        payload = b"\xAA" * 20
        packet = p._build_rtp_packet(payload, payload_type=8)

        # Header is 12 bytes
        assert len(packet) == 32
        header = struct.unpack(">BBHII", packet[:12])
        assert header[0] == 0x80  # V=2, no padding/ext/csrc
        assert header[1] == 8  # payload type 8
        assert header[2] == 100  # sequence number
        assert header[3] == 16000  # timestamp
        assert header[4] == 0x87654321  # SSRC
        assert packet[12:] == payload


@pytest.mark.unit
class TestRTPPlayerPlayBeep:
    """Tests for RTPPlayer.play_beep."""

    def test_play_beep_success(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        with (
            patch("pbx.utils.audio.generate_beep_tone", return_value=b"\x00" * 8000) as mock_gen,
            patch("pbx.utils.audio.pcm16_to_ulaw", return_value=b"\x00" * 4000) as mock_conv,
            patch.object(p, "send_audio", return_value=True) as mock_send,
        ):
            result = p.play_beep(frequency=440, duration_ms=200)

        assert result is True
        mock_gen.assert_called_once_with(440, 200, sample_rate=8000)
        mock_conv.assert_called_once_with(b"\x00" * 8000)
        mock_send.assert_called_once_with(b"\x00" * 4000, payload_type=0)

    def test_play_beep_import_error(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        with patch.dict("sys.modules", {"pbx.utils.audio": None}):
            # Force ImportError by making the import fail
            import builtins
            original_import = builtins.__import__

            def failing_import(name, *args, **kwargs):
                if name == "pbx.utils.audio":
                    raise ImportError("no module")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=failing_import):
                result = p.play_beep()

        assert result is False


@pytest.mark.unit
class TestRTPPlayerPlayFile:
    """Tests for RTPPlayer.play_file."""

    def test_file_not_found(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        with patch.object(Path, "exists", return_value=False):
            result = p.play_file("/nonexistent/file.wav")
        assert result is False

    def _build_wav(
        self,
        audio_format: int = 7,
        num_channels: int = 1,
        sample_rate: int = 8000,
        bits_per_sample: int = 8,
        audio_data: bytes = b"\x00" * 160,
        extra_fmt_bytes: bytes = b"",
    ) -> bytes:
        """Build a minimal WAV file for testing."""
        # fmt chunk
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        fmt_data = struct.pack(
            "<HHIIHH",
            audio_format, num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
        )
        fmt_chunk = b"fmt " + struct.pack("<I", len(fmt_data) + len(extra_fmt_bytes)) + fmt_data + extra_fmt_bytes

        # data chunk
        data_chunk = b"data" + struct.pack("<I", len(audio_data)) + audio_data

        # RIFF header
        riff_size = 4 + len(fmt_chunk) + len(data_chunk)
        return b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + fmt_chunk + data_chunk

    def test_play_ulaw_file(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        wav_data = self._build_wav(audio_format=7, sample_rate=8000, bits_per_sample=8)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch.object(p, "send_audio", return_value=True) as mock_send,
        ):
            result = p.play_file("/test/file.wav")

        assert result is True
        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[0][1] == 0  # payload_type PCMU

    def test_play_alaw_file(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        wav_data = self._build_wav(audio_format=6, sample_rate=8000, bits_per_sample=8)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch.object(p, "send_audio", return_value=True) as mock_send,
        ):
            result = p.play_file("/test/file.wav")

        assert result is True
        args = mock_send.call_args
        assert args[0][1] == 8  # payload_type PCMA

    def test_play_g722_file(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        wav_data = self._build_wav(audio_format=0x0067, sample_rate=16000, bits_per_sample=8)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch.object(p, "send_audio", return_value=True) as mock_send,
        ):
            result = p.play_file("/test/file.wav")

        assert result is True
        args = mock_send.call_args
        assert args[0][1] == 9  # payload_type G.722
        # G.722 should set sample_rate=16000 for samples_per_packet calculation
        assert args[0][2] == 320  # 16000 * 0.02

    def test_play_pcm_file_8khz(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        audio_data = b"\x00\x01" * 160  # 320 bytes of 16-bit PCM
        wav_data = self._build_wav(
            audio_format=1, sample_rate=8000, bits_per_sample=16, audio_data=audio_data,
        )
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch("pbx.utils.audio.pcm16_to_ulaw", return_value=b"\x00" * 160) as mock_conv,
            patch.object(p, "send_audio", return_value=True) as mock_send,
        ):
            result = p.play_file("/test/file.wav")

        assert result is True
        mock_conv.assert_called_once()
        args = mock_send.call_args
        assert args[0][1] == 0  # payload_type PCMU (converted)

    def test_play_pcm_file_16khz_downsampled(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        # 320 bytes (160 16-bit samples at 16kHz)
        audio_data = b"\x00\x01" * 160
        wav_data = self._build_wav(
            audio_format=1, sample_rate=16000, bits_per_sample=16, audio_data=audio_data,
        )
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch("pbx.utils.audio.pcm16_to_ulaw", return_value=b"\x00" * 80) as mock_conv,
            patch.object(p, "send_audio", return_value=True) as mock_send,
        ):
            result = p.play_file("/test/file.wav")

        assert result is True

    def test_play_unsupported_format(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        wav_data = self._build_wav(audio_format=99)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_stereo_pcm(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        # Stereo 16-bit PCM
        audio_data = b"\x00\x01\x02\x03" * 80  # 320 bytes interleaved stereo
        wav_data = self._build_wav(
            audio_format=1, num_channels=2, sample_rate=8000, bits_per_sample=16,
            audio_data=audio_data,
        )
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch("pbx.utils.audio.pcm16_to_ulaw", return_value=b"\x00" * 80) as mock_conv,
            patch.object(p, "send_audio", return_value=True) as mock_send,
        ):
            result = p.play_file("/test/file.wav")
        assert result is True

    def test_play_stereo_8bit(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        audio_data = b"\xAA\xBB" * 80  # 160 bytes stereo 8-bit
        wav_data = self._build_wav(
            audio_format=7, num_channels=2, sample_rate=8000, bits_per_sample=8,
            audio_data=audio_data,
        )
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch.object(p, "send_audio", return_value=True) as mock_send,
        ):
            result = p.play_file("/test/file.wav")
        assert result is True

    def test_play_bad_riff(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=b"BAAD" + b"\x00" * 40)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_bad_wave_marker(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        data = b"RIFF" + struct.pack("<I", 100) + b"BAAD"
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=data)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_truncated_size(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        data = b"RIFF\x00"
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=data)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_empty_data_chunk(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        wav_data = self._build_wav(audio_data=b"")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_data_chunk_too_large(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        # Build WAV manually with oversized data chunk size
        fmt_data = struct.pack("<HHIIHH", 7, 1, 8000, 8000, 1, 8)
        fmt_chunk = b"fmt " + struct.pack("<I", 16) + fmt_data
        # Data chunk with unreasonable size
        data_chunk = b"data" + struct.pack("<I", 200 * 1024 * 1024)
        riff_size = 4 + len(fmt_chunk) + 8
        wav_data = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + fmt_chunk + data_chunk
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_data_before_fmt(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        # Build WAV with data chunk before fmt chunk
        data_chunk = b"data" + struct.pack("<I", 160) + b"\x00" * 160
        fmt_data = struct.pack("<HHIIHH", 7, 1, 8000, 8000, 1, 8)
        fmt_chunk = b"fmt " + struct.pack("<I", 16) + fmt_data
        riff_size = 4 + len(data_chunk) + len(fmt_chunk)
        wav_data = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + data_chunk + fmt_chunk
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_extra_fmt_bytes(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        wav_data = self._build_wav(
            audio_format=7, extra_fmt_bytes=b"\x00\x00",
        )
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch.object(p, "send_audio", return_value=True),
        ):
            result = p.play_file("/test/file.wav")
        assert result is True

    def test_play_oserror(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", side_effect=OSError("read error")),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_pcm_conversion_error(self) -> None:
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        audio_data = b"\x00\x01" * 160
        wav_data = self._build_wav(
            audio_format=1, sample_rate=8000, bits_per_sample=16, audio_data=audio_data,
        )
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch("pbx.utils.audio.pcm16_to_ulaw", side_effect=ValueError("convert fail")),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_unknown_chunk_skipped(self) -> None:
        """Test that unknown chunks before fmt are skipped."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        # Build WAV with unknown chunk before fmt
        unknown_chunk = b"JUNK" + struct.pack("<I", 4) + b"\x00\x00\x00\x00"
        fmt_data = struct.pack("<HHIIHH", 7, 1, 8000, 8000, 1, 8)
        fmt_chunk = b"fmt " + struct.pack("<I", 16) + fmt_data
        audio_data = b"\x00" * 160
        data_chunk = b"data" + struct.pack("<I", len(audio_data)) + audio_data
        riff_size = 4 + len(unknown_chunk) + len(fmt_chunk) + len(data_chunk)
        wav_data = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + unknown_chunk + fmt_chunk + data_chunk

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
            patch.object(p, "send_audio", return_value=True),
        ):
            result = p.play_file("/test/file.wav")
        assert result is True

    def test_play_skip_chunk_too_large_in_data_search(self) -> None:
        """Test that oversized non-data chunk in data search causes failure."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        fmt_data = struct.pack("<HHIIHH", 7, 1, 8000, 8000, 1, 8)
        fmt_chunk = b"fmt " + struct.pack("<I", 16) + fmt_data
        # Non-data chunk with huge size in data search loop
        huge_chunk = b"JUNK" + struct.pack("<I", 200 * 1024 * 1024)
        riff_size = 4 + len(fmt_chunk) + 8
        wav_data = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + fmt_chunk + huge_chunk

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False

    def test_play_fmt_chunk_too_small(self) -> None:
        """Test that fmt chunk size < 16 causes failure."""
        with patch("pbx.rtp.handler.get_logger"):
            from pbx.rtp.handler import RTPPlayer

            p = RTPPlayer(local_port=5000, remote_host="10.0.0.1", remote_port=6000)

        # fmt chunk with size=8 (too small)
        fmt_chunk = b"fmt " + struct.pack("<I", 8) + b"\x00" * 8
        riff_size = 4 + len(fmt_chunk)
        wav_data = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + fmt_chunk

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data=wav_data)),
        ):
            result = p.play_file("/test/file.wav")
        assert result is False


# ---------------------------------------------------------------------------
# RTPDTMFListener tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRTPDTMFListenerInit:
    """Tests for RTPDTMFListener.__init__."""

    def test_init_defaults(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector") as mock_detector_cls,
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        assert listener.local_port == 5000
        assert listener.call_id == "unknown"
        assert listener.running is False
        assert listener.detected_digits == []
        assert listener.sample_rate == 8000

    def test_init_with_call_id(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000, call_id="c1")

        assert listener.call_id == "c1"


@pytest.mark.unit
class TestRTPDTMFListenerStart:
    """Tests for RTPDTMFListener.start."""

    def test_start_success(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        mock_sock = MagicMock()
        with (
            patch("pbx.rtp.handler.socket.socket", return_value=mock_sock),
            patch("pbx.rtp.handler.threading.Thread") as mock_thread_cls,
        ):
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            result = listener.start()

        assert result is True
        assert listener.running is True
        mock_sock.settimeout.assert_called_once_with(0.1)

    def test_start_failure(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        with patch("pbx.rtp.handler.socket.socket", side_effect=OSError("fail")):
            result = listener.start()

        assert result is False


@pytest.mark.unit
class TestRTPDTMFListenerStop:
    """Tests for RTPDTMFListener.stop."""

    def test_stop_with_socket(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        mock_sock = MagicMock()
        listener.socket = mock_sock
        listener.running = True
        listener.stop()
        assert listener.running is False
        assert listener.socket is None
        mock_sock.close.assert_called_once()

    def test_stop_socket_close_oserror(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("close error")
        listener.socket = mock_sock
        listener.running = True
        listener.stop()  # Should not raise
        assert listener.socket is None

    def test_stop_no_socket(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        listener.running = True
        listener.stop()
        assert listener.running is False


@pytest.mark.unit
class TestRTPDTMFListenerListenLoop:
    """Tests for RTPDTMFListener._listen_loop."""

    def test_listen_processes_ulaw(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector") as mock_detector_cls,
        ):
            mock_detector = MagicMock()
            mock_detector.detect_tone.return_value = None
            mock_detector_cls.return_value = mock_detector
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        # Build ulaw RTP packet (payload_type=0)
        rtp_header = struct.pack("!BBHII", 0x80, 0, 1, 160, 0xDEADBEEF)
        # Need enough payload to trigger buffer processing (410+ samples)
        payload = b"\x80" * 420
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            listener.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        listener.socket = mock_sock
        listener.running = True
        listener._listen_loop()

    def test_listen_detects_digit(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector") as mock_detector_cls,
        ):
            mock_detector = MagicMock()
            mock_detector.detect_tone.return_value = "5"
            mock_detector_cls.return_value = mock_detector
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        rtp_header = struct.pack("!BBHII", 0x80, 0, 1, 160, 0xDEADBEEF)
        payload = b"\x80" * 420
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            listener.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        listener.socket = mock_sock
        listener.running = True
        listener._listen_loop()
        assert "5" in listener.detected_digits

    def test_listen_no_duplicate_digit(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector") as mock_detector_cls,
        ):
            mock_detector = MagicMock()
            mock_detector.detect_tone.return_value = "5"
            mock_detector_cls.return_value = mock_detector
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        listener.detected_digits = ["5"]  # Already have a "5"

        rtp_header = struct.pack("!BBHII", 0x80, 0, 1, 160, 0xDEADBEEF)
        payload = b"\x80" * 420
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            listener.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        listener.socket = mock_sock
        listener.running = True
        listener._listen_loop()
        # Should not add duplicate
        assert listener.detected_digits == ["5"]

    def test_listen_processes_alaw(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector") as mock_detector_cls,
        ):
            mock_detector = MagicMock()
            mock_detector.detect_tone.return_value = None
            mock_detector_cls.return_value = mock_detector
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        # A-law (payload_type=8)
        rtp_header = struct.pack("!BBHII", 0x80, 8, 1, 160, 0xDEADBEEF)
        payload = b"\x80" * 420
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            listener.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        listener.socket = mock_sock
        listener.running = True
        listener._listen_loop()

    def test_listen_ignores_non_g711(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector") as mock_detector_cls,
        ):
            mock_detector = MagicMock()
            mock_detector_cls.return_value = mock_detector
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        # Payload type 9 (G.722) - not in [0, 8]
        rtp_header = struct.pack("!BBHII", 0x80, 9, 1, 160, 0xDEADBEEF)
        payload = b"\x00" * 160
        packet = rtp_header + payload

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (packet, ("10.0.0.1", 6000))
            listener.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        listener.socket = mock_sock
        listener.running = True
        listener._listen_loop()
        mock_detector.detect_tone.assert_not_called()

    def test_listen_short_packet(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (b"\x00" * 5, ("10.0.0.1", 6000))
            listener.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        listener.socket = mock_sock
        listener.running = True
        listener._listen_loop()

    def test_listen_timeout(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("timeout")
            listener.running = False
            raise OSError("done")

        mock_sock.recvfrom.side_effect = recv_side_effect
        listener.socket = mock_sock
        listener.running = True
        listener._listen_loop()

    def test_listen_oserror(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        mock_sock = MagicMock()
        call_count = 0

        def recv_side_effect(size):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                listener.running = False
            raise OSError("net error")

        mock_sock.recvfrom.side_effect = recv_side_effect
        listener.socket = mock_sock
        listener.running = True
        listener._listen_loop()


@pytest.mark.unit
class TestRTPDTMFListenerDecodeG711:
    """Tests for RTPDTMFListener._decode_g711."""

    def test_decode_ulaw(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        samples = listener._decode_g711(b"\x80\x00\xFF", payload_type=0)
        assert len(samples) == 3
        for s in samples:
            assert -1.0 <= s <= 1.0

    def test_decode_alaw(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        samples = listener._decode_g711(b"\x80\x00\xFF", payload_type=8)
        assert len(samples) == 3
        for s in samples:
            assert -1.0 <= s <= 1.0


@pytest.mark.unit
class TestRTPDTMFListenerUlawToLinear:
    """Tests for RTPDTMFListener._ulaw_to_linear."""

    def test_positive_output(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        # sign bit 0 -> positive
        result = listener._ulaw_to_linear(0xFF)  # ~0xFF = 0x00; sign=0
        assert result > 0

    def test_negative_output(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        # ~0x7F = 0x80; sign=1 -> negative
        result = listener._ulaw_to_linear(0x7F)
        assert result < 0

    def test_various_bytes(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        for b in [0, 64, 128, 200, 255]:
            result = listener._ulaw_to_linear(b)
            assert isinstance(result, int)


@pytest.mark.unit
class TestRTPDTMFListenerAlawToLinear:
    """Tests for RTPDTMFListener._alaw_to_linear."""

    def test_exponent_zero(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        # After XOR with 0x55: need exponent=0 and sign=0
        # alaw_byte ^ 0x55 should give exponent=0 (bits 4-6 all zero) and sign=0 (bit 7=0)
        # 0x55 ^ 0x55 = 0x00 -> exponent=0, sign=0, mantissa=0
        result = listener._alaw_to_linear(0x55)
        assert result == 8  # (0 << 4) + 8

    def test_exponent_nonzero(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        # 0x65 ^ 0x55 = 0x30 -> sign=0, exponent=3, mantissa=0
        result = listener._alaw_to_linear(0x65)
        # ((0 << 4) + 0x108) << (3-1) = 0x108 << 2 = 264 << 2 = 1056
        assert result == 1056

    def test_negative_output(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        # Need sign=1 after XOR: bit 7 = 1
        # alaw_byte ^ 0x55 must have bit 7 set
        # 0xD5 ^ 0x55 = 0x80 -> sign=1, exponent=0, mantissa=0
        result = listener._alaw_to_linear(0xD5)
        assert result == -8

    def test_various_bytes(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        for b in [0, 64, 128, 200, 255]:
            result = listener._alaw_to_linear(b)
            assert isinstance(result, int)


@pytest.mark.unit
class TestRTPDTMFListenerGetDigit:
    """Tests for RTPDTMFListener.get_digit."""

    def test_get_digit_available(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        listener.detected_digits = ["1", "2", "3"]
        result = listener.get_digit(timeout=0.1)
        assert result == "1"
        assert listener.detected_digits == ["2", "3"]

    def test_get_digit_timeout(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        with patch("pbx.rtp.handler.time.sleep"):
            with patch("pbx.rtp.handler.time.time", side_effect=[0.0, 0.0, 2.0]):
                result = listener.get_digit(timeout=1.0)
        assert result is None


@pytest.mark.unit
class TestRTPDTMFListenerClearDigits:
    """Tests for RTPDTMFListener.clear_digits."""

    def test_clear(self) -> None:
        with (
            patch("pbx.rtp.handler.get_logger"),
            patch("pbx.utils.dtmf.DTMFDetector"),
        ):
            from pbx.rtp.handler import RTPDTMFListener

            listener = RTPDTMFListener(local_port=5000)

        listener.detected_digits = ["1", "2", "3"]
        listener.clear_digits()
        assert listener.detected_digits == []
