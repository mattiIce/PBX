"""
Comprehensive tests for AutoAttendantHandler (pbx.core.auto_attendant_handler).

Covers:
  - __init__
  - handle_auto_attendant (happy path, no SDP, no RTP ports, codec negotiation)
  - _auto_attendant_session (no caller RTP, player start failure, DTMF listener failure,
                              welcome greeting from file / generated, main menu from file / generated,
                              DTMF transfer, DTMF play, SIP INFO DTMF, timeout, error handling,
                              port cleanup on error, port cleanup on success)
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

# Pre-mock modules that use Python 3.12+ syntax or have heavy dependencies
_mock_rtp_handler = MagicMock()
_mock_utils_audio = MagicMock()
_mock_sip_message = MagicMock()
_mock_sip_sdp = MagicMock()

sys.modules.setdefault("pbx.rtp.handler", _mock_rtp_handler)
sys.modules.setdefault("pbx.utils.audio", _mock_utils_audio)
sys.modules.setdefault("pbx.sip.message", _mock_sip_message)
sys.modules.setdefault("pbx.sip.sdp", _mock_sip_sdp)

from pbx.core.auto_attendant_handler import AutoAttendantHandler


def _make_pbx_core() -> MagicMock:
    """Create a fully-wired MagicMock acting as PBXCore."""
    pbx = MagicMock()
    pbx.logger = MagicMock()
    pbx.config.get.return_value = 5060
    pbx._get_server_ip.return_value = "10.0.0.1"
    pbx._get_phone_user_agent.return_value = "TestAgent/1.0"
    pbx._detect_phone_model.return_value = "GenericPhone"
    pbx._get_codecs_for_phone_model.return_value = ["0", "8"]
    pbx._get_dtmf_payload_type.return_value = 101
    pbx._get_ilbc_mode.return_value = 30
    pbx.rtp_relay.port_pool = [30000, 30002, 30004]
    pbx.auto_attendant.timeout = 30
    return pbx


def _make_call(state_value: str = "connected") -> MagicMock:
    """Create a mock Call object."""
    call_obj = MagicMock()
    call_obj.rtp_ports = (30000, 30001)
    call_obj.caller_rtp = {"address": "192.168.1.10", "port": 40000}
    call_obj.caller_addr = ("192.168.1.10", 5060)
    call_obj.auto_attendant_active = True
    call_obj.aa_rtp_port = 30000
    call_obj.dtmf_info_queue = []
    state = MagicMock()
    state.value = state_value
    call_obj.state = state
    return call_obj


def _make_message(with_body: bool = True) -> MagicMock:
    """Create a mock SIP message."""
    message = MagicMock()
    if with_body:
        message.body = "v=0\r\no=- 0 0 IN IP4 192.168.1.10\r\n"
    else:
        message.body = None
    return message


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAutoAttendantHandlerInit:
    """Tests for AutoAttendantHandler initialisation."""

    def test_init_stores_pbx_core(self) -> None:
        """Handler should store the pbx_core reference."""
        pbx = MagicMock()
        handler = AutoAttendantHandler(pbx)
        assert handler.pbx_core is pbx


# ---------------------------------------------------------------------------
# handle_auto_attendant
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleAutoAttendant:
    """Tests for handle_auto_attendant."""

    @patch("threading.Thread")
    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_happy_path_returns_true(
        self, mock_sip, mock_sdp_builder, mock_sdp_session, mock_thread_cls
    ) -> None:
        """Successful auto attendant setup should return True."""
        pbx = _make_pbx_core()
        handler = AutoAttendantHandler(pbx)
        message = _make_message()

        session_data = {"session": {"state": "MAIN_MENU"}, "file": None}
        pbx.auto_attendant.start_session.return_value = session_data

        result = handler.handle_auto_attendant(
            "1001", "0", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True
        pbx.call_manager.create_call.assert_called_once_with("call-1", "1001", "0")
        pbx.cdr_system.start_record.assert_called_once_with("call-1", "1001", "0")

    @patch("threading.Thread")
    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_no_sdp_body(
        self, mock_sip, mock_sdp_builder, mock_sdp_session, mock_thread_cls
    ) -> None:
        """When INVITE has no SDP body, should still proceed."""
        pbx = _make_pbx_core()
        handler = AutoAttendantHandler(pbx)
        message = _make_message(with_body=False)

        session_data = {"session": {"state": "MAIN_MENU"}, "file": None}
        pbx.auto_attendant.start_session.return_value = session_data

        result = handler.handle_auto_attendant(
            "1001", "0", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True

    def test_no_rtp_ports_returns_false(self) -> None:
        """When RTP port pool is empty, should return False."""
        pbx = _make_pbx_core()
        pbx.rtp_relay.port_pool = []  # Empty pool
        handler = AutoAttendantHandler(pbx)
        message = _make_message()

        result = handler.handle_auto_attendant(
            "1001", "0", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is False
        pbx.logger.error.assert_called()

    @patch("threading.Thread")
    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_sends_180_ringing(
        self, mock_sip_builder, mock_sdp_builder, mock_sdp_session, mock_thread_cls
    ) -> None:
        """Should send 180 Ringing before answering."""
        pbx = _make_pbx_core()
        handler = AutoAttendantHandler(pbx)
        message = _make_message()

        session_data = {"session": {"state": "MAIN_MENU"}, "file": None}
        pbx.auto_attendant.start_session.return_value = session_data

        handler.handle_auto_attendant("1001", "0", "call-1", message, ("192.168.1.10", 5060))

        # build_response should be called at least twice (180 and 200)
        assert mock_sip_builder.build_response.call_count >= 2

    @patch("threading.Thread")
    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_detected_phone_model_logged(
        self, mock_sip, mock_sdp_builder, mock_sdp_session, mock_thread_cls
    ) -> None:
        """When phone model is detected, codec info should be logged."""
        pbx = _make_pbx_core()
        pbx._detect_phone_model.return_value = "Polycom VVX"
        handler = AutoAttendantHandler(pbx)
        message = _make_message()

        session_data = {"session": {"state": "MAIN_MENU"}, "file": None}
        pbx.auto_attendant.start_session.return_value = session_data

        handler.handle_auto_attendant("1001", "0", "call-1", message, ("192.168.1.10", 5060))
        pbx._get_codecs_for_phone_model.assert_called()

    @patch("threading.Thread")
    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_no_phone_model_uses_default_codecs(
        self, mock_sip, mock_sdp_builder, mock_sdp_session, mock_thread_cls
    ) -> None:
        """When no phone model is detected, should use default codecs."""
        pbx = _make_pbx_core()
        pbx._detect_phone_model.return_value = None
        handler = AutoAttendantHandler(pbx)
        message = _make_message()

        session_data = {"session": {"state": "MAIN_MENU"}, "file": None}
        pbx.auto_attendant.start_session.return_value = session_data

        handler.handle_auto_attendant("1001", "0", "call-1", message, ("192.168.1.10", 5060))
        # Should still succeed
        pbx.sip_server._send_message.assert_called()

    @patch("threading.Thread")
    @patch("pbx.sip.sdp.SDPSession")
    @patch("pbx.sip.sdp.SDPBuilder")
    @patch("pbx.sip.message.SIPMessageBuilder")
    def test_rtp_port_allocated_from_pool(
        self, mock_sip, mock_sdp_builder, mock_sdp_session, mock_thread_cls
    ) -> None:
        """The first port from the pool should be allocated for the call."""
        pbx = _make_pbx_core()
        pbx.rtp_relay.port_pool = [40000, 40002]
        handler = AutoAttendantHandler(pbx)
        message = _make_message()

        session_data = {"session": {"state": "MAIN_MENU"}, "file": None}
        pbx.auto_attendant.start_session.return_value = session_data

        handler.handle_auto_attendant("1001", "0", "call-1", message, ("192.168.1.10", 5060))
        # 40000 should have been popped
        assert 40000 not in pbx.rtp_relay.port_pool


# ---------------------------------------------------------------------------
# _auto_attendant_session
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAutoAttendantSession:
    """Tests for _auto_attendant_session."""

    @patch("pbx.core.auto_attendant_handler.time")
    def test_no_caller_rtp_returns_early(self, mock_time) -> None:
        """If no caller RTP, should log warning and eventually end call."""
        pbx = _make_pbx_core()
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        call_obj.caller_rtp = None
        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        handler._auto_attendant_session("call-1", call_obj, session)
        pbx.logger.warning.assert_called()
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_player_start_failure(self, mock_player_cls, mock_time) -> None:
        """If RTP player fails to start, should return and end call."""
        pbx = _make_pbx_core()
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = False
        mock_player_cls.return_value = mock_player

        handler._auto_attendant_session("call-1", call_obj, session)
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_dtmf_listener_start_failure(self, mock_player_cls, mock_dtmf_cls, mock_time) -> None:
        """If DTMF listener fails to start, should stop player and end call."""
        pbx = _make_pbx_core()
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = False
        mock_dtmf_cls.return_value = mock_dtmf

        handler._auto_attendant_session("call-1", call_obj, session)
        mock_player.stop.assert_called()
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_welcome_audio_from_file(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """When welcome audio file exists, should play it directly."""
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 0  # Immediate timeout to exit loop
        pbx.auto_attendant.handle_timeout.return_value = {"action": "hangup"}
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()

        session = {"session": {"state": "MAIN_MENU"}, "file": "/audio/welcome.wav"}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = None
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"PROMPT_AUDIO"

        with patch.object(Path, "exists", return_value=True):
            handler._auto_attendant_session("call-1", call_obj, session)

        # play_file should have been called for the welcome file
        assert mock_player.play_file.called

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_welcome_audio_generated(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """When no welcome file exists, should generate prompt audio."""
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 0
        pbx.auto_attendant.handle_timeout.return_value = {"action": "hangup"}
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = None
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"GENERATED_WELCOME"

        handler._auto_attendant_session("call-1", call_obj, session)

        mock_get_prompt.assert_any_call("welcome", prompt_dir="auto_attendant")

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_dtmf_transfer_action(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """On DTMF resulting in transfer, should call transfer_call."""
        mock_time.time.return_value = 100.0
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 60
        pbx.auto_attendant.handle_dtmf.return_value = {
            "action": "transfer",
            "destination": "8001",
            "session": {"state": "TRANSFERRING"},
        }
        pbx.transfer_call.return_value = True
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        call_obj.dtmf_info_queue = ["1"]

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = None
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"TRANSFER_AUDIO"

        handler._auto_attendant_session("call-1", call_obj, session)

        pbx.transfer_call.assert_called_with("call-1", "8001")

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_dtmf_transfer_failure_logged(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """If transfer_call returns False, a warning should be logged."""
        mock_time.time.return_value = 100.0
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 60
        pbx.auto_attendant.handle_dtmf.return_value = {
            "action": "transfer",
            "destination": "8001",
            "session": {"state": "TRANSFERRING"},
        }
        pbx.transfer_call.return_value = False
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        call_obj.dtmf_info_queue = ["1"]

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        handler._auto_attendant_session("call-1", call_obj, session)
        pbx.logger.warning.assert_called()

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_dtmf_play_action_resets_timeout(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """On DTMF play action, timeout should be reset."""
        mock_time.time.return_value = 100.0
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 60

        call_count = [0]

        def mock_handle_dtmf(session, digit):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "action": "play",
                    "file": None,
                    "session": {"state": "SUB_MENU"},
                }
            return {
                "action": "transfer",
                "destination": "1001",
                "session": {"state": "TRANSFERRING"},
            }

        pbx.auto_attendant.handle_dtmf.side_effect = mock_handle_dtmf
        pbx.transfer_call.return_value = True
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        call_obj.dtmf_info_queue = ["3", "2"]

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = None
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        handler._auto_attendant_session("call-1", call_obj, session)
        # Two DTMF digits processed
        assert pbx.auto_attendant.handle_dtmf.call_count == 2

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_timeout_triggers_transfer(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """When session times out, should handle timeout and potentially transfer."""
        mock_time.time.return_value = 100.0
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 0  # Immediate timeout
        pbx.auto_attendant.handle_timeout.return_value = {
            "action": "transfer",
            "destination": "1001",
        }
        pbx.transfer_call.return_value = True
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = None
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        handler._auto_attendant_session("call-1", call_obj, session)

        pbx.auto_attendant.handle_timeout.assert_called()
        pbx.transfer_call.assert_called()

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_timeout_transfer_failure_logged(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """When timeout transfer fails, a warning should be logged."""
        mock_time.time.return_value = 100.0
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 0
        pbx.auto_attendant.handle_timeout.return_value = {
            "action": "transfer",
            "destination": "1001",
        }
        pbx.transfer_call.return_value = False
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = None
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        handler._auto_attendant_session("call-1", call_obj, session)
        pbx.logger.warning.assert_called()

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_port_returned_on_success(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """RTP port should be returned to pool after session ends."""
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 0
        pbx.auto_attendant.handle_timeout.return_value = {"action": "hangup"}
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        call_obj.aa_rtp_port = 30000

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = None
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        handler._auto_attendant_session("call-1", call_obj, session)

        assert 30000 in pbx.rtp_relay.port_pool

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_error_in_session_returns_port(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """On error, RTP port should still be returned to the pool."""
        pbx = _make_pbx_core()
        pbx.rtp_relay.port_pool = [30002]
        pbx.auto_attendant._get_audio_file.return_value = None
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        call_obj.aa_rtp_port = 30000

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.side_effect = TypeError("bad type")
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        handler._auto_attendant_session("call-1", call_obj, session)
        assert 30000 in pbx.rtp_relay.port_pool
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_inband_dtmf_processed(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """In-band DTMF detection should be used when SIP INFO queue is empty."""
        mock_time.time.return_value = 100.0
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = None
        pbx.auto_attendant.timeout = 60
        pbx.auto_attendant.handle_dtmf.return_value = {
            "action": "transfer",
            "destination": "8001",
            "session": {"state": "TRANSFERRING"},
        }
        pbx.transfer_call.return_value = True
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        call_obj.dtmf_info_queue = []  # Empty SIP INFO queue

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = "1"  # In-band digit
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        handler._auto_attendant_session("call-1", call_obj, session)
        pbx.auto_attendant.handle_dtmf.assert_called()

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_transfer_audio_from_file(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """When transferring audio file exists, should play it directly."""
        mock_time.time.return_value = 100.0
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.side_effect = lambda name: (
            "/audio/transferring.wav" if name == "transferring" else None
        )
        pbx.auto_attendant.timeout = 60
        pbx.auto_attendant.handle_dtmf.return_value = {
            "action": "transfer",
            "destination": "8001",
            "session": {"state": "TRANSFERRING"},
        }
        pbx.transfer_call.return_value = True
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()
        call_obj.dtmf_info_queue = ["1"]

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        with patch.object(Path, "exists", return_value=True):
            handler._auto_attendant_session("call-1", call_obj, session)

        # transfer should still happen
        pbx.transfer_call.assert_called()

    @patch("pbx.core.auto_attendant_handler.time")
    @patch("pbx.utils.audio.get_prompt_audio")
    @patch("pbx.rtp.handler.RTPDTMFListener")
    @patch("pbx.rtp.handler.RTPPlayer")
    def test_main_menu_audio_from_file(
        self, mock_player_cls, mock_dtmf_cls, mock_get_prompt, mock_time
    ) -> None:
        """When main_menu audio file exists, should play it directly."""
        pbx = _make_pbx_core()
        pbx.auto_attendant._get_audio_file.return_value = "/audio/main_menu.wav"
        pbx.auto_attendant.timeout = 0
        pbx.auto_attendant.handle_timeout.return_value = {"action": "hangup"}
        handler = AutoAttendantHandler(pbx)
        call_obj = _make_call()

        session = {"session": {"state": "MAIN_MENU"}, "file": None}

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        mock_dtmf = MagicMock()
        mock_dtmf.start.return_value = True
        mock_dtmf.get_digit.return_value = None
        mock_dtmf_cls.return_value = mock_dtmf

        mock_get_prompt.return_value = b"AUDIO"

        with patch.object(Path, "exists", return_value=True):
            handler._auto_attendant_session("call-1", call_obj, session)

        assert mock_player.play_file.called
