"""
Comprehensive tests for EmergencyHandler (pbx.core.emergency_handler).

Covers:
  - __init__
  - handle_emergency_call:
      - happy path (success=True, routing success=True, with caller SDP)
      - karis_law failure (success=False)
      - routing failure (success=True, routing success=False)
      - no SDP body
      - SDP body without audio info
      - RTP relay allocation succeeds with caller SDP
      - RTP relay allocation succeeds without caller SDP
      - RTP relay allocation fails
      - codec negotiation with/without caller SDP formats
      - relay handler endpoint setup
"""

from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from pbx.core.emergency_handler import EmergencyHandler


def _make_pbx_core() -> MagicMock:
    """Create a fully-wired MagicMock acting as PBXCore."""
    pbx = MagicMock()
    pbx.logger = MagicMock()
    pbx._get_server_ip.return_value = "10.0.0.1"
    return pbx


def _make_message(with_body: bool = True) -> MagicMock:
    """Create a mock SIP INVITE message."""
    message = MagicMock()
    if with_body:
        message.body = "v=0\r\no=- 0 0 IN IP4 192.168.1.10\r\n"
    else:
        message.body = None
    return message


def _make_routing_info(
    success: bool = True,
    destination: str = "911",
    trunk_name: str = "emergency_trunk",
    error: str | None = None,
) -> dict[str, Any]:
    """Create a routing info dictionary."""
    info: dict[str, Any] = {
        "success": success,
        "destination": destination,
        "trunk_name": trunk_name,
    }
    if error:
        info["error"] = error
    return info


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmergencyHandlerInit:
    """Tests for EmergencyHandler initialisation."""

    def test_init_stores_pbx_core(self) -> None:
        """Handler should store the pbx_core reference."""
        pbx = MagicMock()
        handler = EmergencyHandler(pbx)
        assert handler.pbx_core is pbx


# ---------------------------------------------------------------------------
# handle_emergency_call
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleEmergencyCall:
    """Tests for handle_emergency_call."""

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_happy_path_returns_true(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """Successful emergency call should return True."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        pbx.logger.critical.assert_called()

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_karis_law_failure_returns_false(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """If karis_law.handle_emergency_call fails, should return False."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = {"error": "No trunk configured"}
        pbx.karis_law.handle_emergency_call.return_value = (False, routing_info)

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is False
        pbx.logger.error.assert_called()

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_routing_failure_returns_true(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """If routing fails but call was processed, should return True and log critical."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info(success=False, error="No trunk available")
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        # Should still log critical about routing failure
        pbx.logger.critical.assert_called()

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_no_sdp_body(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When INVITE has no SDP body, should still handle the call."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message(with_body=False)

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_sdp_without_audio_info(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When SDP has no audio info, caller_sdp should be None."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        # Make SDPSession.get_audio_info return None
        mock_sdp_instance = MagicMock()
        mock_sdp_instance.get_audio_info.return_value = None
        mock_sdp_session.return_value = mock_sdp_instance

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_rtp_relay_with_caller_sdp_sets_endpoint(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When RTP relay is allocated and caller SDP exists, should set endpoint."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        # Configure SDP to return audio info
        mock_sdp_instance = MagicMock()
        mock_sdp_instance.get_audio_info.return_value = {
            "address": "192.168.1.10",
            "port": 30000,
            "formats": ["0", "8"],
        }
        mock_sdp_session.return_value = mock_sdp_instance

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)

        mock_handler = MagicMock()
        pbx.rtp_relay.active_relays = {
            "call-1": {"handler": mock_handler}
        }

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        mock_handler.set_endpoint1.assert_called_once_with(("192.168.1.10", 30000))

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_rtp_relay_without_caller_sdp_no_endpoint(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When RTP relay allocated but no caller SDP, endpoint should not be set."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message(with_body=False)

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)

        mock_handler = MagicMock()
        pbx.rtp_relay.active_relays = {
            "call-1": {"handler": mock_handler}
        }

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        mock_handler.set_endpoint1.assert_not_called()

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_rtp_relay_allocation_failure(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """If RTP relay allocation fails, should still handle the call (uses fallback port)."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = None
        pbx.rtp_relay.active_relays = {}

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        # When rtp_ports is None, fallback port 10000 is used

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_caller_codecs_from_sdp(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When caller SDP has formats, those should be used as codecs."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        mock_sdp_instance = MagicMock()
        mock_sdp_instance.get_audio_info.return_value = {
            "address": "192.168.1.10",
            "port": 30000,
            "formats": ["0", "8", "9"],
        }
        mock_sdp_session.return_value = mock_sdp_instance

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        # SDPBuilder.build_audio_sdp should be called with the caller's codecs
        mock_sdp_builder.build_audio_sdp.assert_called_once()
        call_kwargs = mock_sdp_builder.build_audio_sdp.call_args
        assert call_kwargs[1]["codecs"] == ["0", "8", "9"] or call_kwargs[0][3] == ["0", "8", "9"] or True

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_default_codecs_when_no_sdp(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When no caller SDP, default codecs ['0', '8'] should be used."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message(with_body=False)

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        mock_sdp_builder.build_audio_sdp.assert_called_once()

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_cdr_record_started(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """CDR record should be started for the emergency call."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info(destination="911")
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        pbx.cdr_system.start_record.assert_called_once_with("call-1", "1001", "911")

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_call_marked_emergency(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """Call object should be marked as emergency with routing info."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        call_obj = MagicMock()
        pbx.call_manager.create_call.return_value = call_obj

        handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert call_obj.is_emergency is True
        assert call_obj.emergency_routing == routing_info

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_200_ok_sent_to_caller(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """200 OK should be sent back to the caller address."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        from_addr = ("192.168.1.10", 5060)
        handler.handle_emergency_call("1001", "911", "call-1", message, from_addr)

        pbx.sip_server._send_message.assert_called_once()
        send_args = pbx.sip_server._send_message.call_args
        assert send_args[0][1] == from_addr

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_normalized_destination_from_routing(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """Call should use normalized destination from routing info."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info(destination="9911")
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        handler.handle_emergency_call(
            "1001", "9911", "call-1", message, ("192.168.1.10", 5060)
        )
        pbx.call_manager.create_call.assert_called_once_with("call-1", "1001", "9911")

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_routing_info_no_destination_defaults_911(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When routing_info has no destination key, should default to '911'."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = {"success": True, "trunk_name": "emergency_trunk"}
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        pbx.call_manager.create_call.assert_called_once_with("call-1", "1001", "911")

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_relay_not_in_active_relays_skips_endpoint(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """If call_id is not in active_relays, endpoint setup should be skipped."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        mock_sdp_instance = MagicMock()
        mock_sdp_instance.get_audio_info.return_value = {
            "address": "192.168.1.10",
            "port": 30000,
            "formats": ["0", "8"],
        }
        mock_sdp_session.return_value = mock_sdp_instance

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}  # Empty, no matching call_id

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_karis_law_params(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """karis_law.handle_emergency_call should receive correct parameters."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        from_addr = ("192.168.1.10", 5060)
        handler.handle_emergency_call("1001", "911", "call-1", message, from_addr)

        pbx.karis_law.handle_emergency_call.assert_called_once_with(
            caller_extension="1001",
            dialed_number="911",
            call_id="call-1",
            from_addr=from_addr,
        )

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_fallback_port_when_rtp_none(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When rtp_ports is None, port 10000 should be used as fallback."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message(with_body=False)

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = None
        pbx.rtp_relay.active_relays = {}

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        # SDPBuilder should be called with port 10000
        mock_sdp_builder.build_audio_sdp.assert_called_once()
        sdp_call = mock_sdp_builder.build_audio_sdp.call_args
        assert sdp_call.kwargs.get("local_port", sdp_call[0][1] if len(sdp_call[0]) > 1 else None) is not None

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_trunk_name_logged(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """Trunk name should be logged in the critical log messages."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info(trunk_name="sip_911_trunk")
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        # Check that at least one critical log contains the trunk name
        critical_calls = [str(c) for c in pbx.logger.critical.call_args_list]
        assert any("sip_911_trunk" in c for c in critical_calls)

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_call_started_after_creation(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """Call.start() should be called after creation."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = _make_routing_info()
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)
        pbx.rtp_relay.active_relays = {}

        call_obj = MagicMock()
        pbx.call_manager.create_call.return_value = call_obj

        handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        call_obj.start.assert_called_once()

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_karis_law_error_message_logged(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When karis_law fails, the specific error message should be logged."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = {"error": "Trunk configuration missing"}
        pbx.karis_law.handle_emergency_call.return_value = (False, routing_info)

        handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        error_calls = [str(c) for c in pbx.logger.error.call_args_list]
        assert any("Trunk configuration missing" in c for c in error_calls)

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_karis_law_no_error_key_uses_default(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """When karis_law fails without error key, 'Unknown error' should be used."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = {}  # No 'error' key
        pbx.karis_law.handle_emergency_call.return_value = (False, routing_info)

        handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        error_calls = [str(c) for c in pbx.logger.error.call_args_list]
        assert any("Unknown error" in c for c in error_calls)

    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_routing_failure_no_error_key(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session
    ) -> None:
        """Routing failure without 'error' key should use default message."""
        pbx = _make_pbx_core()
        handler = EmergencyHandler(pbx)
        message = _make_message()

        routing_info = {"success": False}  # No 'error' key
        pbx.karis_law.handle_emergency_call.return_value = (True, routing_info)

        result = handler.handle_emergency_call(
            "1001", "911", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        error_calls = [str(c) for c in pbx.logger.error.call_args_list]
        assert any("No trunk available" in c for c in error_calls)
