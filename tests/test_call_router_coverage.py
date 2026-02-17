"""Comprehensive tests for pbx/core/call_router.py - Call routing logic."""

import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from pbx.core.call_router import CallRouter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pbx_core(
    *,
    config_overrides: dict[str, Any] | None = None,
    extension_registered: bool = True,
    dialplan: dict[str, str] | None = None,
) -> MagicMock:
    """Build a comprehensive mock PBXCore."""
    pbx = MagicMock()

    # Config mock with side_effect-based get
    config_data: dict[str, Any] = {
        "server.sip_port": 5060,
        "voicemail.no_answer_timeout": 30,
        "voicemail.max_message_duration": 180,
        "sip.caller_id.send_p_asserted_identity": True,
        "sip.caller_id.send_remote_party_id": True,
        "sip.device.send_mac_address": True,
        "sip.device.accept_mac_in_invite": True,
    }
    if dialplan is not None:
        config_data["dialplan"] = dialplan
    if config_overrides:
        config_data.update(config_overrides)

    def config_get(key: str, default: Any = None) -> Any:
        return config_data.get(key, default)

    pbx.config = MagicMock()
    pbx.config.get.side_effect = config_get

    # Logger
    pbx.logger = MagicMock()

    # Extension registry
    pbx.extension_registry = MagicMock()
    pbx.extension_registry.is_registered.return_value = extension_registered

    dest_ext = MagicMock()
    dest_ext.address = ("10.0.0.2", 5060)
    dest_ext.name = "Test User"
    pbx.extension_registry.get.return_value = dest_ext

    # Kari's law
    pbx.karis_law = MagicMock()
    pbx.karis_law.is_emergency_number.return_value = False

    # Auto attendant
    pbx.auto_attendant = MagicMock()
    pbx.auto_attendant.get_extension.return_value = "0"

    # Paging system
    pbx.paging_system = MagicMock()
    pbx.paging_system.is_paging_extension.return_value = False

    # Call manager
    mock_call = MagicMock()
    mock_call.start_time = MagicMock()
    mock_call.start_time.isoformat.return_value = "2026-01-01T00:00:00+00:00"
    mock_call.rtp_ports = None
    mock_call.caller_rtp = None
    mock_call.caller_addr = None
    mock_call.callee_addr = None
    mock_call.original_invite = None
    mock_call.no_answer_timer = None
    mock_call.routed_to_voicemail = False
    mock_call.from_extension = "1001"
    mock_call.to_extension = "1002"
    pbx.call_manager = MagicMock()
    pbx.call_manager.create_call.return_value = mock_call
    pbx.call_manager.get_call.return_value = mock_call

    # CDR
    pbx.cdr_system = MagicMock()

    # Webhook
    pbx.webhook_system = MagicMock()

    # RTP relay
    pbx.rtp_relay = MagicMock()
    pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
    pbx.rtp_relay.active_relays = {}

    # SIP server
    pbx.sip_server = MagicMock()

    # Server IP
    pbx._get_server_ip.return_value = "10.0.0.1"

    # Phone model detection
    pbx._get_phone_user_agent.return_value = "Generic/1.0"
    pbx._detect_phone_model.return_value = None
    pbx._get_codecs_for_phone_model.return_value = ["PCMU", "PCMA"]

    # DTMF / iLBC config
    pbx._get_dtmf_payload_type.return_value = 101
    pbx._get_ilbc_mode.return_value = 30

    # Registered phones DB
    pbx.registered_phones_db = MagicMock()
    pbx.registered_phones_db.get_by_extension.return_value = []

    # WebRTC
    pbx.webrtc_gateway = None

    # Voicemail handler and system
    pbx._voicemail_handler = MagicMock()
    pbx._emergency_handler = MagicMock()
    pbx._auto_attendant_handler = MagicMock()
    pbx._paging_handler = MagicMock()
    pbx.voicemail_system = MagicMock()

    return pbx


def _make_invite_message(
    *,
    from_ext: str = "1001",
    to_ext: str = "1002",
    call_id: str = "test-call-id-123",
    body: str = "",
    via: str = "SIP/2.0/UDP 10.0.0.1:5060;branch=z9hG4bK776",
    cseq: str = "1 INVITE",
    extra_headers: dict[str, str] | None = None,
) -> MagicMock:
    """Build a mock SIP INVITE message."""
    msg = MagicMock()
    msg.body = body

    headers: dict[str, str] = {
        "From": f"<sip:{from_ext}@pbx.local>;tag=abc123",
        "To": f"<sip:{to_ext}@pbx.local>",
        "Call-ID": call_id,
        "CSeq": cseq,
        "Via": via,
    }
    if extra_headers:
        headers.update(extra_headers)

    msg.get_header.side_effect = headers.get
    msg.uri = f"sip:{to_ext}@pbx.local"
    return msg


CALLER_ADDR = ("192.168.1.100", 5060)


# ===========================================================================
# CallRouter.__init__
# ===========================================================================


@pytest.mark.unit
class TestCallRouterInit:
    """Tests for CallRouter initialization."""

    def test_init_stores_pbx_core(self) -> None:
        pbx = MagicMock()
        router = CallRouter(pbx)
        assert router.pbx_core is pbx


# ===========================================================================
# CallRouter._check_dialplan
# ===========================================================================


@pytest.mark.unit
class TestCheckDialplan:
    """Tests for _check_dialplan() method."""

    def test_emergency_pattern_911(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("911") is True

    def test_emergency_pattern_9911(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("9911") is True

    def test_internal_extension_1001(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("1001") is True

    def test_internal_extension_1999(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("1999") is True

    def test_conference_extension_2001(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("2001") is True

    def test_voicemail_pattern_star_1001(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("*1001") is True

    def test_voicemail_pattern_star_3digits(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("*100") is True

    def test_auto_attendant_pattern_0(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("0") is True

    def test_parking_pattern_70(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("70") is True

    def test_parking_pattern_79(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("79") is True

    def test_queue_pattern_8001(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("8001") is True

    def test_invalid_extension_rejected(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("5555") is False

    def test_invalid_short_extension_rejected(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("99") is False

    def test_custom_internal_pattern(self) -> None:
        pbx = _make_pbx_core(dialplan={"internal_pattern": "^3[0-9]{3}$"})
        router = CallRouter(pbx)
        assert router._check_dialplan("3001") is True
        assert router._check_dialplan("1001") is False

    def test_empty_dialplan_uses_defaults(self) -> None:
        pbx = _make_pbx_core(dialplan={})
        router = CallRouter(pbx)
        assert router._check_dialplan("1001") is True

    def test_no_dialplan_config(self) -> None:
        pbx = _make_pbx_core()
        router = CallRouter(pbx)
        assert router._check_dialplan("1001") is True


# ===========================================================================
# CallRouter.route_call - header parsing
# ===========================================================================


@pytest.mark.unit
class TestRouteCallHeaderParsing:
    """Tests for route_call() SIP header parsing."""

    def test_invalid_from_header_returns_false(self) -> None:
        pbx = _make_pbx_core()
        router = CallRouter(pbx)

        result = router.route_call(
            "invalid-no-sip-uri",
            "<sip:1002@pbx.local>",
            "call-1",
            _make_invite_message(),
            CALLER_ADDR,
        )
        assert result is False

    def test_invalid_to_header_returns_false(self) -> None:
        pbx = _make_pbx_core()
        router = CallRouter(pbx)

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "invalid-no-sip-uri",
            "call-1",
            _make_invite_message(),
            CALLER_ADDR,
        )
        assert result is False


# ===========================================================================
# CallRouter.route_call - emergency calls
# ===========================================================================


@pytest.mark.unit
class TestRouteCallEmergency:
    """Tests for emergency call routing."""

    def test_emergency_call_routed_to_handler(self) -> None:
        pbx = _make_pbx_core()
        pbx.karis_law.is_emergency_number.return_value = True
        pbx._emergency_handler.handle_emergency_call.return_value = True

        router = CallRouter(pbx)
        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:911@pbx.local>",
            "call-911",
            _make_invite_message(to_ext="911"),
            CALLER_ADDR,
        )

        assert result is True
        pbx._emergency_handler.handle_emergency_call.assert_called_once()


# ===========================================================================
# CallRouter.route_call - auto attendant
# ===========================================================================


@pytest.mark.unit
class TestRouteCallAutoAttendant:
    """Tests for auto attendant routing."""

    def test_auto_attendant_call_routed(self) -> None:
        pbx = _make_pbx_core()
        pbx.auto_attendant.get_extension.return_value = "0"
        pbx._auto_attendant_handler.handle_auto_attendant.return_value = True

        router = CallRouter(pbx)
        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:0@pbx.local>",
            "call-aa",
            _make_invite_message(to_ext="0"),
            CALLER_ADDR,
        )

        assert result is True
        pbx._auto_attendant_handler.handle_auto_attendant.assert_called_once()


# ===========================================================================
# CallRouter.route_call - voicemail access
# ===========================================================================


@pytest.mark.unit
class TestRouteCallVoicemailAccess:
    """Tests for voicemail access (*xxxx) routing."""

    def test_voicemail_access_star_4digits(self) -> None:
        pbx = _make_pbx_core()
        pbx._voicemail_handler.handle_voicemail_access.return_value = True

        router = CallRouter(pbx)
        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:*1002@pbx.local>",
            "call-vm",
            _make_invite_message(to_ext="*1002"),
            CALLER_ADDR,
        )

        assert result is True
        pbx._voicemail_handler.handle_voicemail_access.assert_called_once()

    def test_voicemail_access_star_3digits(self) -> None:
        pbx = _make_pbx_core()
        pbx._voicemail_handler.handle_voicemail_access.return_value = True

        router = CallRouter(pbx)
        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:*100@pbx.local>",
            "call-vm",
            _make_invite_message(to_ext="*100"),
            CALLER_ADDR,
        )

        assert result is True
        pbx._voicemail_handler.handle_voicemail_access.assert_called_once()

    def test_voicemail_access_too_short_not_routed(self) -> None:
        """*12 is too short (len < 4), not voicemail access."""
        pbx = _make_pbx_core()
        router = CallRouter(pbx)

        # *12 won't match voicemail pattern, will go through normal routing
        # which may fail at dialplan or extension check
        router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:*12@pbx.local>",
            "call-vm",
            _make_invite_message(to_ext="*12"),
            CALLER_ADDR,
        )

        pbx._voicemail_handler.handle_voicemail_access.assert_not_called()

    def test_voicemail_access_too_long_not_routed(self) -> None:
        """*12345 is too long (len > 5), not voicemail access."""
        pbx = _make_pbx_core()
        router = CallRouter(pbx)

        router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:*12345@pbx.local>",
            "call-vm",
            _make_invite_message(to_ext="*12345"),
            CALLER_ADDR,
        )

        pbx._voicemail_handler.handle_voicemail_access.assert_not_called()


# ===========================================================================
# CallRouter.route_call - paging
# ===========================================================================


@pytest.mark.unit
class TestRouteCallPaging:
    """Tests for paging system routing."""

    def test_paging_call_routed(self) -> None:
        pbx = _make_pbx_core()
        pbx.paging_system.is_paging_extension.return_value = True
        pbx._paging_handler.handle_paging.return_value = True

        router = CallRouter(pbx)
        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:700@pbx.local>",
            "call-page",
            _make_invite_message(to_ext="700"),
            CALLER_ADDR,
        )

        assert result is True
        pbx._paging_handler.handle_paging.assert_called_once()


# ===========================================================================
# CallRouter.route_call - extension not registered
# ===========================================================================


@pytest.mark.unit
class TestRouteCallUnregistered:
    """Tests for unregistered extension handling."""

    def test_unregistered_extension_returns_false(self) -> None:
        pbx = _make_pbx_core(extension_registered=False)
        router = CallRouter(pbx)

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            _make_invite_message(),
            CALLER_ADDR,
        )

        assert result is False
        pbx.logger.warning.assert_called()


# ===========================================================================
# CallRouter.route_call - dialplan check
# ===========================================================================


@pytest.mark.unit
class TestRouteCallDialplanCheck:
    """Tests for dialplan check in route_call."""

    def test_dialplan_rejected_returns_false(self) -> None:
        pbx = _make_pbx_core(
            dialplan={"internal_pattern": "^3[0-9]{3}$"},
        )
        # Extension 1002 does not match 3xxx pattern
        router = CallRouter(pbx)

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            _make_invite_message(),
            CALLER_ADDR,
        )

        assert result is False


# ===========================================================================
# CallRouter.route_call - SDP parsing
# ===========================================================================


@pytest.mark.unit
class TestRouteCallSDP:
    """Tests for SDP parsing in route_call."""

    @patch("pbx.sip.sdp.SDPBuilder.build_audio_sdp", return_value="v=0\r\n")
    @patch("pbx.sip.sdp.SDPSession")
    def test_caller_sdp_parsed_with_body(
        self, mock_sdp_cls: MagicMock, mock_build_sdp: MagicMock
    ) -> None:
        pbx = _make_pbx_core()

        sdp_obj = MagicMock()
        sdp_obj.get_audio_info.return_value = {
            "address": "192.168.1.100",
            "port": 30000,
            "formats": ["PCMU", "PCMA"],
        }
        mock_sdp_cls.return_value = sdp_obj

        router = CallRouter(pbx)
        msg = _make_invite_message(body="v=0\r\no=- 0 0 IN IP4 192.168.1.100")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_no_sdp_body_still_routes(self) -> None:
        pbx = _make_pbx_core()
        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    @patch("pbx.sip.sdp.SDPBuilder.build_audio_sdp", return_value="v=0\r\n")
    @patch("pbx.sip.sdp.SDPSession")
    def test_sdp_with_no_audio_info(
        self, mock_sdp_cls: MagicMock, mock_build_sdp: MagicMock
    ) -> None:
        pbx = _make_pbx_core()

        sdp_obj = MagicMock()
        sdp_obj.get_audio_info.return_value = None
        mock_sdp_cls.return_value = sdp_obj

        router = CallRouter(pbx)
        msg = _make_invite_message(body="v=0\r\n")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True


# ===========================================================================
# CallRouter.route_call - RTP relay setup
# ===========================================================================


@pytest.mark.unit
class TestRouteCallRTPRelay:
    """Tests for RTP relay allocation and endpoint setup."""

    @patch("pbx.sip.sdp.SDPBuilder.build_audio_sdp", return_value="v=0\r\n")
    @patch("pbx.sip.sdp.SDPSession")
    def test_rtp_relay_allocated_and_endpoint_set(
        self, mock_sdp_cls: MagicMock, mock_build_sdp: MagicMock
    ) -> None:
        pbx = _make_pbx_core()

        sdp_obj = MagicMock()
        sdp_obj.get_audio_info.return_value = {
            "address": "192.168.1.100",
            "port": 30000,
            "formats": ["PCMU"],
        }
        mock_sdp_cls.return_value = sdp_obj

        # Setup active relay info
        mock_handler = MagicMock()
        pbx.rtp_relay.active_relays = {"call-1": {"handler": mock_handler}}

        router = CallRouter(pbx)
        msg = _make_invite_message(body="v=0\r\n")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True
        pbx.rtp_relay.allocate_relay.assert_called_once_with("call-1")
        mock_handler.set_endpoints.assert_called_once_with(("192.168.1.100", 30000), None)

    def test_rtp_relay_allocation_returns_none(self) -> None:
        pbx = _make_pbx_core()
        pbx.rtp_relay.allocate_relay.return_value = None

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        # Still returns True; rtp_ports is None so the SDP forward block is skipped
        assert result is True


# ===========================================================================
# CallRouter.route_call - destination extension handling
# ===========================================================================


@pytest.mark.unit
class TestRouteCallDestination:
    """Tests for destination extension address resolution."""

    def test_dest_ext_no_address_returns_false(self) -> None:
        pbx = _make_pbx_core()
        dest_ext = MagicMock()
        dest_ext.address = None
        pbx.extension_registry.get.return_value = dest_ext

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is False

    def test_dest_ext_not_found_returns_false(self) -> None:
        pbx = _make_pbx_core()
        pbx.extension_registry.get.return_value = None

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is False


# ===========================================================================
# CallRouter.route_call - WebRTC routing
# ===========================================================================


@pytest.mark.unit
class TestRouteCallWebRTC:
    """Tests for WebRTC destination routing."""

    def test_webrtc_destination_success(self) -> None:
        pbx = _make_pbx_core()
        dest_ext = MagicMock()
        dest_ext.address = ("webrtc", "session-abc")
        pbx.extension_registry.get.return_value = dest_ext
        pbx.webrtc_gateway = MagicMock()
        pbx.webrtc_gateway.receive_call.return_value = True

        router = CallRouter(pbx)
        msg = _make_invite_message(body="v=0\r\n")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True
        pbx.webrtc_gateway.receive_call.assert_called_once()

    def test_webrtc_destination_receive_call_fails(self) -> None:
        pbx = _make_pbx_core()
        dest_ext = MagicMock()
        dest_ext.address = ("webrtc", "session-abc")
        pbx.extension_registry.get.return_value = dest_ext
        pbx.webrtc_gateway = MagicMock()
        pbx.webrtc_gateway.receive_call.return_value = False

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is False

    def test_webrtc_destination_no_gateway(self) -> None:
        pbx = _make_pbx_core()
        dest_ext = MagicMock()
        dest_ext.address = ("webrtc", "session-abc")
        pbx.extension_registry.get.return_value = dest_ext
        pbx.webrtc_gateway = None

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is False


# ===========================================================================
# CallRouter.route_call - SIP INVITE forwarding
# ===========================================================================


@pytest.mark.unit
class TestRouteCallInviteForwarding:
    """Tests for INVITE forwarding to callee."""

    def test_invite_forwarded_to_callee(self) -> None:
        pbx = _make_pbx_core()
        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True
        pbx.sip_server._send_message.assert_called_once()

    def test_caller_id_headers_added(self) -> None:
        pbx = _make_pbx_core()

        caller_ext = MagicMock()
        caller_ext.name = "John Doe"

        def get_ext(ext_num: str) -> MagicMock:
            if ext_num == "1001":
                return caller_ext
            dest = MagicMock()
            dest.address = ("10.0.0.2", 5060)
            return dest

        pbx.extension_registry.get.side_effect = get_ext

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        # The INVITE built by SIPMessageBuilder should have caller ID headers set
        # We verify via the sip_server._send_message being called (means forwarding happened)
        pbx.sip_server._send_message.assert_called_once()

    def test_caller_id_headers_skipped_when_disabled(self) -> None:
        pbx = _make_pbx_core(
            config_overrides={
                "sip.caller_id.send_p_asserted_identity": False,
                "sip.caller_id.send_remote_party_id": False,
            }
        )

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_caller_ext_with_empty_name_uses_extension_number(self) -> None:
        pbx = _make_pbx_core()

        caller_ext = MagicMock()
        caller_ext.name = ""

        def get_ext(ext_num: str) -> MagicMock:
            if ext_num == "1001":
                return caller_ext
            dest = MagicMock()
            dest.address = ("10.0.0.2", 5060)
            return dest

        pbx.extension_registry.get.side_effect = get_ext

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        # Should not raise
        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_caller_ext_not_found_uses_ext_number_as_name(self) -> None:
        pbx = _make_pbx_core()

        def get_ext(ext_num: str) -> MagicMock | None:
            if ext_num == "1001":
                return None
            dest = MagicMock()
            dest.address = ("10.0.0.2", 5060)
            return dest

        pbx.extension_registry.get.side_effect = get_ext

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True


# ===========================================================================
# CallRouter.route_call - MAC address handling
# ===========================================================================


@pytest.mark.unit
class TestRouteCallMACAddress:
    """Tests for MAC address header handling."""

    def test_mac_from_registered_phones_db(self) -> None:
        pbx = _make_pbx_core()
        pbx.registered_phones_db.get_by_extension.return_value = [
            {"mac_address": "AA:BB:CC:DD:EE:FF"}
        ]

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        pbx.sip_server._send_message.assert_called_once()

    def test_mac_from_invite_x_mac_header(self) -> None:
        pbx = _make_pbx_core()
        pbx.registered_phones_db.get_by_extension.return_value = []

        router = CallRouter(pbx)
        msg = _make_invite_message(
            body="",
            extra_headers={"X-MAC-Address": "11:22:33:44:55:66"},
        )

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_mac_disabled_in_config(self) -> None:
        pbx = _make_pbx_core(
            config_overrides={
                "sip.device.send_mac_address": False,
            }
        )

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_mac_db_lookup_exception(self) -> None:
        pbx = _make_pbx_core()
        pbx.registered_phones_db.get_by_extension.side_effect = KeyError("db error")

        router = CallRouter(pbx)
        msg = _make_invite_message(
            body="",
            extra_headers={"X-MAC-Address": "AA:BB:CC:DD:EE:FF"},
        )

        # Should not raise
        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_no_mac_available(self) -> None:
        pbx = _make_pbx_core()
        pbx.registered_phones_db.get_by_extension.return_value = []

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_mac_db_returns_empty_mac(self) -> None:
        pbx = _make_pbx_core()
        pbx.registered_phones_db.get_by_extension.return_value = [{"mac_address": None}]

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_mac_accept_from_invite_disabled(self) -> None:
        pbx = _make_pbx_core(
            config_overrides={
                "sip.device.accept_mac_in_invite": False,
            }
        )
        pbx.registered_phones_db.get_by_extension.return_value = []

        router = CallRouter(pbx)
        msg = _make_invite_message(
            body="",
            extra_headers={"X-MAC-Address": "11:22:33:44:55:66"},
        )

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True


# ===========================================================================
# CallRouter.route_call - no-answer timer
# ===========================================================================


@pytest.mark.unit
class TestRouteCallNoAnswerTimer:
    """Tests for no-answer timer setup in route_call."""

    def test_no_answer_timer_started(self) -> None:
        pbx = _make_pbx_core()
        mock_call = pbx.call_manager.create_call.return_value

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True
        # Verify the no_answer_timer was assigned on the call object
        assert mock_call.no_answer_timer is not None


# ===========================================================================
# CallRouter.route_call - CDR and webhooks
# ===========================================================================


@pytest.mark.unit
class TestRouteCallCDRWebhooks:
    """Tests for CDR and webhook triggering."""

    def test_cdr_record_started(self) -> None:
        pbx = _make_pbx_core()
        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        pbx.cdr_system.start_record.assert_called_once_with("call-1", "1001", "1002")

    def test_webhook_triggered(self) -> None:
        pbx = _make_pbx_core()
        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        pbx.webhook_system.trigger_event.assert_called_once()
        webhook_args = pbx.webhook_system.trigger_event.call_args
        from pbx.features.webhooks import WebhookEvent

        assert webhook_args[0][0] == WebhookEvent.CALL_STARTED


# ===========================================================================
# CallRouter._send_cancel_to_callee
# ===========================================================================


@pytest.mark.unit
class TestSendCancelToCallee:
    """Tests for _send_cancel_to_callee()."""

    def test_sends_cancel_to_callee(self) -> None:
        pbx = _make_pbx_core()

        mock_call = MagicMock()
        mock_call.callee_addr = ("10.0.0.2", 5060)
        mock_call.callee_invite = MagicMock()
        mock_call.callee_invite.uri = "sip:1002@10.0.0.1"
        _callee_headers = {
            "From": "<sip:1001@pbx.local>",
            "To": "<sip:1002@pbx.local>",
            "CSeq": "1 INVITE",
            "Via": "SIP/2.0/UDP 10.0.0.1:5060",
        }
        mock_call.callee_invite.get_header.side_effect = _callee_headers.get
        mock_call.to_extension = "1002"

        router = CallRouter(pbx)
        router._send_cancel_to_callee(mock_call, "call-1")

        pbx.sip_server._send_message.assert_called_once()

    def test_no_callee_addr_returns_early(self) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.callee_addr = None
        mock_call.callee_invite = MagicMock()

        router = CallRouter(pbx)
        router._send_cancel_to_callee(mock_call, "call-1")

        pbx.sip_server._send_message.assert_not_called()

    def test_no_callee_invite_returns_early(self) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock(spec=[])  # Empty spec so hasattr returns False
        mock_call.callee_addr = ("10.0.0.2", 5060)

        router = CallRouter(pbx)
        router._send_cancel_to_callee(mock_call, "call-1")

        pbx.sip_server._send_message.assert_not_called()


# ===========================================================================
# CallRouter._answer_call_for_voicemail
# ===========================================================================


@pytest.mark.unit
class TestAnswerCallForVoicemail:
    """Tests for _answer_call_for_voicemail()."""

    def test_answer_success(self) -> None:
        pbx = _make_pbx_core()

        mock_call = MagicMock()
        mock_call.original_invite = MagicMock()
        mock_call.caller_addr = CALLER_ADDR
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000, "formats": ["PCMU"]}
        mock_call.rtp_ports = (20000, 20001)
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"

        router = CallRouter(pbx)
        result = router._answer_call_for_voicemail(mock_call, "call-1")

        assert result is True
        pbx.sip_server._send_message.assert_called_once()
        mock_call.connect.assert_called_once()

    def test_answer_missing_original_invite(self) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.original_invite = None
        mock_call.caller_addr = CALLER_ADDR
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = (20000, 20001)

        router = CallRouter(pbx)
        result = router._answer_call_for_voicemail(mock_call, "call-1")

        assert result is False

    def test_answer_missing_caller_addr(self) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.original_invite = MagicMock()
        mock_call.caller_addr = None
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = (20000, 20001)

        router = CallRouter(pbx)
        result = router._answer_call_for_voicemail(mock_call, "call-1")

        assert result is False

    def test_answer_missing_caller_rtp(self) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.original_invite = MagicMock()
        mock_call.caller_addr = CALLER_ADDR
        mock_call.caller_rtp = None
        mock_call.rtp_ports = (20000, 20001)

        router = CallRouter(pbx)
        result = router._answer_call_for_voicemail(mock_call, "call-1")

        assert result is False

    def test_answer_missing_rtp_ports(self) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.original_invite = MagicMock()
        mock_call.caller_addr = CALLER_ADDR
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = None

        router = CallRouter(pbx)
        result = router._answer_call_for_voicemail(mock_call, "call-1")

        assert result is False


# ===========================================================================
# CallRouter._handle_no_answer
# ===========================================================================


@pytest.mark.unit
class TestHandleNoAnswer:
    """Tests for _handle_no_answer() method."""

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_call_not_found(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player: MagicMock,
        mock_rtp_recorder: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        pbx.call_manager.get_call.return_value = None

        router = CallRouter(pbx)
        router._handle_no_answer("call-nonexistent")

        pbx.logger.warning.assert_called()

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_call_already_connected(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player: MagicMock,
        mock_rtp_recorder: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = mock_call_state.CONNECTED
        mock_call.routed_to_voicemail = False
        pbx.call_manager.get_call.return_value = mock_call

        router = CallRouter(pbx)
        router._handle_no_answer("call-1")

        pbx.logger.debug.assert_called()

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_already_routed_to_voicemail(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player: MagicMock,
        mock_rtp_recorder: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = True
        pbx.call_manager.get_call.return_value = mock_call

        router = CallRouter(pbx)
        router._handle_no_answer("call-1")

        pbx.logger.debug.assert_called()

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_no_answer_routes_to_voicemail(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player_cls: MagicMock,
        mock_rtp_recorder_cls: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = False
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = (20000, 20001)
        mock_call.caller_addr = CALLER_ADDR
        mock_call.original_invite = MagicMock()
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        pbx.call_manager.get_call.return_value = mock_call

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_rtp_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_rtp_recorder_cls.return_value = mock_recorder

        mock_get_prompt.return_value = b"\x00\x01\x02"

        mailbox = MagicMock()
        mailbox.get_greeting_path.return_value = None
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        router = CallRouter(pbx)
        router._answer_call_for_voicemail = MagicMock(return_value=True)
        router._send_cancel_to_callee = MagicMock()

        with (
            patch("threading.Timer") as mock_timer_cls,
            patch("threading.Thread") as mock_thread_cls,
            patch("time.sleep"),
        ):
            mock_timer = MagicMock()
            mock_timer_cls.return_value = mock_timer
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread

            router._handle_no_answer("call-1")

        assert mock_call.routed_to_voicemail is True
        router._send_cancel_to_callee.assert_called_once()
        router._answer_call_for_voicemail.assert_called_once()

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_no_answer_answer_fails_returns_early(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player_cls: MagicMock,
        mock_rtp_recorder_cls: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = False
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        pbx.call_manager.get_call.return_value = mock_call

        router = CallRouter(pbx)
        router._answer_call_for_voicemail = MagicMock(return_value=False)
        router._send_cancel_to_callee = MagicMock()

        router._handle_no_answer("call-1")

        router._answer_call_for_voicemail.assert_called_once()
        mock_rtp_player_cls.assert_not_called()

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_no_answer_no_caller_rtp_ends_call(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player_cls: MagicMock,
        mock_rtp_recorder_cls: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = False
        mock_call.caller_rtp = None
        mock_call.caller_addr = CALLER_ADDR
        mock_call.original_invite = MagicMock()
        mock_call.rtp_ports = (20000, 20001)
        pbx.call_manager.get_call.return_value = mock_call

        router = CallRouter(pbx)
        router._answer_call_for_voicemail = MagicMock(return_value=True)
        router._send_cancel_to_callee = MagicMock()

        router._handle_no_answer("call-1")

        pbx.end_call.assert_called_once_with("call-1")

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_no_answer_player_start_fails(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player_cls: MagicMock,
        mock_rtp_recorder_cls: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = False
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = (20000, 20001)
        mock_call.caller_addr = CALLER_ADDR
        mock_call.original_invite = MagicMock()
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        pbx.call_manager.get_call.return_value = mock_call

        mock_player = MagicMock()
        mock_player.start.return_value = False
        mock_rtp_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_rtp_recorder_cls.return_value = mock_recorder

        mailbox = MagicMock()
        mailbox.get_greeting_path.return_value = None
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        router = CallRouter(pbx)
        router._answer_call_for_voicemail = MagicMock(return_value=True)
        router._send_cancel_to_callee = MagicMock()

        with (
            patch("threading.Timer") as mock_timer_cls,
            patch("threading.Thread") as mock_thread_cls,
        ):
            mock_timer_cls.return_value = MagicMock()
            mock_thread_cls.return_value = MagicMock()

            router._handle_no_answer("call-1")

        pbx.logger.warning.assert_called()

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_no_answer_recorder_start_fails(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player_cls: MagicMock,
        mock_rtp_recorder_cls: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = False
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = (20000, 20001)
        mock_call.caller_addr = CALLER_ADDR
        mock_call.original_invite = MagicMock()
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        pbx.call_manager.get_call.return_value = mock_call

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_rtp_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = False
        mock_rtp_recorder_cls.return_value = mock_recorder

        mock_get_prompt.return_value = b"\x00\x01\x02"

        mailbox = MagicMock()
        mailbox.get_greeting_path.return_value = None
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        router = CallRouter(pbx)
        router._answer_call_for_voicemail = MagicMock(return_value=True)
        router._send_cancel_to_callee = MagicMock()

        with patch("time.sleep"):
            router._handle_no_answer("call-1")

        pbx.end_call.assert_called_once_with("call-1")

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_no_answer_with_custom_greeting(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player_cls: MagicMock,
        mock_rtp_recorder_cls: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = False
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = (20000, 20001)
        mock_call.caller_addr = CALLER_ADDR
        mock_call.original_invite = MagicMock()
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        pbx.call_manager.get_call.return_value = mock_call

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_rtp_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_rtp_recorder_cls.return_value = mock_recorder

        mailbox = MagicMock()
        mailbox.get_greeting_path.return_value = "/tmp/custom_greeting.wav"
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        router = CallRouter(pbx)
        router._answer_call_for_voicemail = MagicMock(return_value=True)
        router._send_cancel_to_callee = MagicMock()

        with (
            patch("threading.Timer") as mock_timer_cls,
            patch("threading.Thread") as mock_thread_cls,
            patch("time.sleep"),
            patch("pbx.core.call_router.Path") as mock_path,
        ):
            mock_timer_cls.return_value = MagicMock()
            mock_thread_cls.return_value = MagicMock()
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.stat.return_value = MagicMock(st_size=1024)
            mock_path.return_value = mock_path_instance

            router._handle_no_answer("call-1")

        mock_player.play_file.assert_called_once_with("/tmp/custom_greeting.wav")
        mock_player.play_beep.assert_called_once_with(frequency=1000, duration_ms=500)

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_no_answer_custom_greeting_file_not_found_falls_back(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player_cls: MagicMock,
        mock_rtp_recorder_cls: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = False
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = (20000, 20001)
        mock_call.caller_addr = CALLER_ADDR
        mock_call.original_invite = MagicMock()
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        pbx.call_manager.get_call.return_value = mock_call

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_rtp_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_rtp_recorder_cls.return_value = mock_recorder

        mock_get_prompt.return_value = b"\x00\x01\x02"

        mailbox = MagicMock()
        mailbox.get_greeting_path.return_value = "/tmp/nonexistent.wav"
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        router = CallRouter(pbx)
        router._answer_call_for_voicemail = MagicMock(return_value=True)
        router._send_cancel_to_callee = MagicMock()

        with (
            patch("threading.Timer") as mock_timer_cls,
            patch("threading.Thread") as mock_thread_cls,
            patch("time.sleep"),
            patch("pbx.core.call_router.Path") as mock_path,
        ):
            mock_timer_cls.return_value = MagicMock()
            mock_thread_cls.return_value = MagicMock()
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value = mock_path_instance

            router._handle_no_answer("call-1")

        mock_get_prompt.assert_called_once_with("leave_message")

    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPRecorder")
    @patch("pbx.rtp.handler.RTPPlayer")
    @patch("pbx.core.call.CallState")
    def test_no_answer_greeting_oserror(
        self,
        mock_call_state: MagicMock,
        mock_rtp_player_cls: MagicMock,
        mock_rtp_recorder_cls: MagicMock,
        mock_get_prompt: MagicMock,
    ) -> None:
        pbx = _make_pbx_core()
        mock_call = MagicMock()
        mock_call.state = "RINGING"
        mock_call.routed_to_voicemail = False
        mock_call.caller_rtp = {"address": "192.168.1.100", "port": 30000}
        mock_call.rtp_ports = (20000, 20001)
        mock_call.caller_addr = CALLER_ADDR
        mock_call.original_invite = MagicMock()
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        pbx.call_manager.get_call.return_value = mock_call

        mock_rtp_player_cls.side_effect = OSError("port in use")

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_rtp_recorder_cls.return_value = mock_recorder

        mailbox = MagicMock()
        mailbox.get_greeting_path.return_value = None
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        router = CallRouter(pbx)
        router._answer_call_for_voicemail = MagicMock(return_value=True)
        router._send_cancel_to_callee = MagicMock()

        with (
            patch("threading.Timer") as mock_timer_cls,
            patch("threading.Thread") as mock_thread_cls,
        ):
            mock_timer_cls.return_value = MagicMock()
            mock_thread_cls.return_value = MagicMock()

            router._handle_no_answer("call-1")

        pbx.logger.error.assert_called()


# ===========================================================================
# CallRouter.route_call - phone model codec selection
# ===========================================================================


@pytest.mark.unit
class TestRouteCallCodecSelection:
    """Tests for phone model detection and codec selection."""

    def test_detected_phone_model_logs_codecs(self) -> None:
        pbx = _make_pbx_core()
        pbx._detect_phone_model.return_value = "ZIP37G"
        pbx._get_codecs_for_phone_model.return_value = ["PCMU", "PCMA"]

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        pbx._detect_phone_model.assert_called()
        pbx._get_codecs_for_phone_model.assert_called()
        pbx.logger.info.assert_called()


# ===========================================================================
# CallRouter.route_call - registered phones DB edge cases
# ===========================================================================


@pytest.mark.unit
class TestRouteCallRegisteredPhonesDB:
    """Tests for registered_phones_db edge cases."""

    def test_registered_phones_db_is_none(self) -> None:
        pbx = _make_pbx_core()
        pbx.registered_phones_db = None

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_registered_phones_db_type_error(self) -> None:
        pbx = _make_pbx_core()
        pbx.registered_phones_db.get_by_extension.side_effect = TypeError("test")

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True

    def test_registered_phones_db_value_error(self) -> None:
        pbx = _make_pbx_core()
        pbx.registered_phones_db.get_by_extension.side_effect = ValueError("test")

        router = CallRouter(pbx)
        msg = _make_invite_message(body="")

        result = router.route_call(
            "<sip:1001@pbx.local>",
            "<sip:1002@pbx.local>",
            "call-1",
            msg,
            CALLER_ADDR,
        )

        assert result is True
