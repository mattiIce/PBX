"""Integration tests for call routing logic.

Tests the CallRouter class and its interaction with PBXCore subsystems,
including dialplan matching, internal call routing, and no-answer fallback.
"""

import re
import threading
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pbx.core.call import Call, CallManager, CallState
from pbx.core.call_router import CallRouter


@pytest.mark.integration
class TestCallRouterInternalRouting:
    """Test that CallRouter correctly routes internal calls."""

    def _make_pbx_core(self, mock_config: MagicMock, mock_database: MagicMock) -> MagicMock:
        """Build a mock PBXCore with all subsystems wired up."""
        pbx = MagicMock()
        pbx.config = mock_config
        pbx.extension_db = mock_database

        # Call manager -- use a real CallManager so state transitions are real
        pbx.call_manager = CallManager()

        # Extension registry
        caller_ext = MagicMock()
        caller_ext.number = "1001"
        caller_ext.name = "Alice"
        caller_ext.registered = True
        caller_ext.address = ("192.168.1.10", 5060)

        callee_ext = MagicMock()
        callee_ext.number = "1002"
        callee_ext.name = "Bob"
        callee_ext.registered = True
        callee_ext.address = ("192.168.1.11", 5060)

        def get_ext(number: str) -> MagicMock | None:
            return {"1001": caller_ext, "1002": callee_ext}.get(number)

        pbx.extension_registry = MagicMock()
        pbx.extension_registry.get.side_effect = get_ext
        pbx.extension_registry.is_registered.side_effect = lambda n: n in ("1001", "1002")
        pbx.extension_registry.get_all.return_value = [caller_ext, callee_ext]

        # RTP relay
        pbx.rtp_relay = MagicMock()
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20002)
        pbx.rtp_relay.active_relays = {}

        # CDR / webhook / other subsystems
        pbx.cdr_system = MagicMock()
        pbx.webhook_system = MagicMock()
        pbx.sip_server = MagicMock()
        pbx.karis_law = None
        pbx.auto_attendant = None
        pbx.paging_system = None
        pbx.webrtc_gateway = None
        pbx.registered_phones_db = None

        # Helper methods
        pbx._get_server_ip.return_value = "10.0.0.1"
        pbx._get_phone_user_agent.return_value = ""
        pbx._detect_phone_model.return_value = None
        pbx._get_codecs_for_phone_model.return_value = None
        pbx._get_dtmf_payload_type.return_value = 101
        pbx._get_ilbc_mode.return_value = 30

        return pbx

    def _make_sip_message(self, from_ext: str = "1001", to_ext: str = "1002") -> MagicMock:
        """Build a minimal mock SIP INVITE message."""
        msg = MagicMock()
        msg.body = None  # No SDP for simplicity
        msg.get_header.side_effect = lambda h: {
            "CSeq": "1 INVITE",
            "Via": "SIP/2.0/UDP 192.168.1.10:5060;branch=z9hG4bK776",
            "From": f"<sip:{from_ext}@pbx.local>;tag=abc",
            "To": f"<sip:{to_ext}@pbx.local>",
        }.get(h, "")
        return msg

    def test_internal_call_creates_call_object(
        self, mock_config: MagicMock, mock_database: MagicMock
    ) -> None:
        """Route an internal call and verify a Call object is created."""
        pbx = self._make_pbx_core(mock_config, mock_database)
        router = CallRouter(pbx)

        from_header = "<sip:1001@pbx.local>"
        to_header = "<sip:1002@pbx.local>"
        call_id = "call-001"
        message = self._make_sip_message()
        from_addr = ("192.168.1.10", 5060)

        result = router.route_call(from_header, to_header, call_id, message, from_addr)

        assert result is True
        call = pbx.call_manager.get_call(call_id)
        assert call is not None
        assert call.from_extension == "1001"
        assert call.to_extension == "1002"
        assert call.state == CallState.CALLING

    def test_internal_call_starts_cdr_record(
        self, mock_config: MagicMock, mock_database: MagicMock
    ) -> None:
        """Verify that a CDR record is started when routing a call."""
        pbx = self._make_pbx_core(mock_config, mock_database)
        router = CallRouter(pbx)

        from_header = "<sip:1001@pbx.local>"
        to_header = "<sip:1002@pbx.local>"
        call_id = "call-cdr-001"
        message = self._make_sip_message()
        from_addr = ("192.168.1.10", 5060)

        router.route_call(from_header, to_header, call_id, message, from_addr)

        pbx.cdr_system.start_record.assert_called_once_with(call_id, "1001", "1002")

    def test_routing_to_unregistered_extension_fails(
        self, mock_config: MagicMock, mock_database: MagicMock
    ) -> None:
        """Calls to unregistered extensions should fail."""
        pbx = self._make_pbx_core(mock_config, mock_database)
        router = CallRouter(pbx)

        from_header = "<sip:1001@pbx.local>"
        to_header = "<sip:9999@pbx.local>"
        call_id = "call-fail-001"
        message = self._make_sip_message(to_ext="9999")
        from_addr = ("192.168.1.10", 5060)

        result = router.route_call(from_header, to_header, call_id, message, from_addr)

        assert result is False

    def test_unparseable_headers_return_false(
        self, mock_config: MagicMock, mock_database: MagicMock
    ) -> None:
        """If from/to headers cannot be parsed, routing should fail."""
        pbx = self._make_pbx_core(mock_config, mock_database)
        router = CallRouter(pbx)

        result = router.route_call(
            "invalid-header", "also-invalid", "call-bad", MagicMock(), ("0.0.0.0", 0)
        )

        assert result is False


@pytest.mark.integration
class TestDialplanMatching:
    """Test that the dialplan checker accepts and rejects patterns correctly."""

    @pytest.fixture
    def router(self, mock_config: MagicMock) -> CallRouter:
        """Create a CallRouter with default dialplan config."""
        pbx = MagicMock()
        pbx.config = mock_config
        return CallRouter(pbx)

    @pytest.mark.parametrize(
        "extension,expected",
        [
            ("1001", True),  # internal 4-digit
            ("1999", True),  # internal 4-digit
            ("2001", True),  # conference
            ("911", True),  # emergency
            ("9911", True),  # legacy emergency
            ("*1001", True),  # voicemail
            ("*123", True),  # voicemail short
            ("0", True),  # auto attendant
            ("70", True),  # parking
            ("8001", True),  # queue
            ("5555", False),  # not matching any pattern
            ("3001", False),  # not matching any pattern
            ("12", False),  # too short for internal
        ],
    )
    def test_dialplan_patterns(self, router: CallRouter, extension: str, expected: bool) -> None:
        """Verify dialplan matching for various extension patterns."""
        result = router._check_dialplan(extension)
        assert result is expected, f"Extension {extension!r}: expected {expected}, got {result}"

    def test_custom_internal_pattern(self, mock_config: MagicMock) -> None:
        """Dialplan should honour a custom internal_pattern from config."""
        mock_config.config["dialplan"] = {"internal_pattern": "^5[0-9]{2}$"}
        pbx = MagicMock()
        pbx.config = mock_config
        router = CallRouter(pbx)

        assert router._check_dialplan("501") is True
        # Default 4-digit range no longer matches (but emergency still works)
        assert router._check_dialplan("1001") is False


@pytest.mark.integration
class TestNoAnswerHandling:
    """Test that the no-answer timer fires and routes to voicemail."""

    def test_no_answer_sets_voicemail_flag(
        self, mock_config: MagicMock, mock_database: MagicMock
    ) -> None:
        """When _handle_no_answer is called, the call should be flagged for voicemail."""
        pbx = MagicMock()
        pbx.config = mock_config
        pbx.call_manager = CallManager()

        # Create a call in CALLING state (not yet answered)
        call = pbx.call_manager.create_call("call-noanswer", "1001", "1002")
        call.start()
        call.caller_rtp = None  # simplify -- skip RTP recording path
        call.original_invite = None

        router = CallRouter(pbx)
        router._handle_no_answer("call-noanswer")

        assert call.routed_to_voicemail is True

    def test_no_answer_skips_already_connected_call(
        self, mock_config: MagicMock, mock_database: MagicMock
    ) -> None:
        """If the call was already answered, no-answer handler should be a no-op."""
        pbx = MagicMock()
        pbx.config = mock_config
        pbx.call_manager = CallManager()

        call = pbx.call_manager.create_call("call-answered", "1001", "1002")
        call.start()
        call.connect()  # simulate answer

        router = CallRouter(pbx)
        router._handle_no_answer("call-answered")

        # Should NOT be routed to voicemail since it was already connected
        assert call.routed_to_voicemail is False

    def test_no_answer_skips_nonexistent_call(
        self, mock_config: MagicMock, mock_database: MagicMock
    ) -> None:
        """_handle_no_answer for a non-existent call should not raise."""
        pbx = MagicMock()
        pbx.config = mock_config
        pbx.call_manager = CallManager()

        router = CallRouter(pbx)
        # Should not raise
        router._handle_no_answer("call-does-not-exist")
