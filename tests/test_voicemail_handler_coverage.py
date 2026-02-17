"""
Comprehensive tests for VoicemailHandler (pbx.core.voicemail_handler).

Covers:
  - __init__
  - handle_voicemail_access (happy path, extension not found, no SDP, RTP allocation failure)
  - _playback_voicemails (no caller RTP, player start failure, empty messages, multiple messages,
                          play_file failure, error paths)
  - _voicemail_ivr_session (call ended early, no caller RTP, player start failure,
                            recorder start failure, IVR actions, DTMF handling, timeout)
  - monitor_voicemail_dtmf (hash detected, loop exit, error path)
  - complete_voicemail_recording (call not found, no recorder, audio present, no audio)
"""

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Pre-mock modules that use Python 3.12+ syntax and cannot be imported
# ---------------------------------------------------------------------------
_mock_rtp_handler = MagicMock()
_mock_utils_audio = MagicMock()
_mock_utils_dtmf = MagicMock()
_mock_sip_message = MagicMock()
_mock_sip_sdp = MagicMock()
_mock_features_voicemail = MagicMock()

# Insert into sys.modules BEFORE importing VoicemailHandler so that inline
# ``from pbx.rtp.handler import ...`` inside the handler methods resolves
# against the mock instead of trying to parse the real file.
sys.modules.setdefault("pbx.rtp.handler", _mock_rtp_handler)
sys.modules.setdefault("pbx.utils.audio", _mock_utils_audio)
sys.modules.setdefault("pbx.utils.dtmf", _mock_utils_dtmf)
sys.modules.setdefault("pbx.sip.message", _mock_sip_message)
sys.modules.setdefault("pbx.sip.sdp", _mock_sip_sdp)
sys.modules.setdefault("pbx.features.voicemail", _mock_features_voicemail)

from pbx.core.voicemail_handler import VoicemailHandler


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
    pbx._build_wav_file.return_value = b"RIFF_WAV_DATA"
    return pbx


def _make_call(state_value: str = "connected") -> MagicMock:
    """Create a mock Call object."""
    call_obj = MagicMock()
    call_obj.rtp_ports = (20000, 20001)
    call_obj.caller_rtp = {"address": "192.168.1.10", "port": 30000}
    call_obj.caller_addr = ("192.168.1.10", 5060)
    call_obj.voicemail_extension = "1001"
    call_obj.to_extension = "1001"
    call_obj.from_extension = "2001"
    call_obj.voicemail_access = True
    state = MagicMock()
    state.value = state_value
    call_obj.state = state
    call_obj.dtmf_info_queue = []
    return call_obj


def _setup_rtp_mocks() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Reset and return fresh RTPPlayer, RTPRecorder, DTMFDetector, get_prompt_audio mocks."""
    mock_player_cls = MagicMock()
    mock_recorder_cls = MagicMock()
    mock_dtmf_cls = MagicMock()
    mock_get_prompt = MagicMock(return_value=b"WAV_AUDIO_DATA")

    _mock_rtp_handler.RTPPlayer = mock_player_cls
    _mock_rtp_handler.RTPRecorder = mock_recorder_cls
    _mock_utils_dtmf.DTMFDetector = mock_dtmf_cls
    _mock_utils_audio.get_prompt_audio = mock_get_prompt

    return mock_player_cls, mock_recorder_cls, mock_dtmf_cls, mock_get_prompt


@pytest.mark.unit
class TestVoicemailHandlerInit:
    """Tests for VoicemailHandler initialisation."""

    def test_init_stores_pbx_core(self) -> None:
        """VoicemailHandler should store the pbx_core reference."""
        pbx = MagicMock()
        handler = VoicemailHandler(pbx)
        assert handler.pbx_core is pbx


# ---------------------------------------------------------------------------
# handle_voicemail_access
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleVoicemailAccess:
    """Tests for handle_voicemail_access."""

    def _build_deps(self) -> tuple[MagicMock, MagicMock, VoicemailHandler]:
        pbx = _make_pbx_core()
        message = MagicMock()
        message.body = "v=0\r\no=- 0 0 IN IP4 192.168.1.10\r\n"
        handler = VoicemailHandler(pbx)
        return pbx, message, handler

    @patch("pbx.core.voicemail_handler.threading")
    def test_happy_path_returns_true(self, mock_threading) -> None:
        """Successful voicemail access should return True."""
        pbx, message, handler = self._build_deps()
        pbx.extension_registry.get.return_value = {"number": "1001"}
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)

        mailbox = MagicMock()
        mailbox.get_messages.return_value = []
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        result = handler.handle_voicemail_access(
            "2001", "*1001", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True

    def test_extension_not_found_returns_false(self) -> None:
        """When target extension does not exist, should return False."""
        pbx, message, handler = self._build_deps()
        pbx.extension_registry.get.return_value = None
        pbx.config.get_extension.return_value = None

        result = handler.handle_voicemail_access(
            "2001", "*9999", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is False

    @patch("pbx.core.voicemail_handler.threading")
    def test_extension_found_in_config_fallback(self, mock_threading) -> None:
        """Extension found via config fallback should still succeed."""
        pbx, message, handler = self._build_deps()
        pbx.extension_registry.get.return_value = None
        pbx.config.get_extension.return_value = {"number": "1001"}
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)

        mailbox = MagicMock()
        mailbox.get_messages.return_value = []
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        result = handler.handle_voicemail_access(
            "2001", "*1001", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True

    @patch("pbx.core.voicemail_handler.threading")
    def test_no_sdp_body_proceeds(self, mock_threading) -> None:
        """When INVITE has no SDP body, should still proceed (caller_sdp=None)."""
        pbx, message, handler = self._build_deps()
        message.body = None
        pbx.extension_registry.get.return_value = {"number": "1001"}
        pbx.rtp_relay.allocate_relay.return_value = (20000, 20001)

        mailbox = MagicMock()
        mailbox.get_messages.return_value = []
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        result = handler.handle_voicemail_access(
            "2001", "*1001", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is True

    def test_rtp_allocation_failure_returns_false(self) -> None:
        """If RTP relay allocation fails, should return False."""
        pbx, message, handler = self._build_deps()
        pbx.extension_registry.get.return_value = {"number": "1001"}
        pbx.rtp_relay.allocate_relay.return_value = None

        mailbox = MagicMock()
        pbx.voicemail_system.get_mailbox.return_value = mailbox

        result = handler.handle_voicemail_access(
            "2001", "*1001", "call-1", message, ("192.168.1.10", 5060)
        )
        assert result is False


# ---------------------------------------------------------------------------
# _playback_voicemails
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPlaybackVoicemails:
    """Tests for _playback_voicemails."""

    @patch("pbx.core.voicemail_handler.time")
    def test_no_caller_rtp_ends_call(self, mock_time) -> None:
        """If no caller RTP info, should end the call after a delay."""
        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.caller_rtp = None

        handler._playback_voicemails("call-1", call_obj, MagicMock(), [])
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.voicemail_handler.time")
    def test_player_start_failure_ends_call(self, mock_time) -> None:
        """If RTP player fails to start, should end the call."""
        mock_player_cls, _, _, _ = _setup_rtp_mocks()
        mock_player = MagicMock()
        mock_player.start.return_value = False
        mock_player_cls.return_value = mock_player

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()

        handler._playback_voicemails("call-1", call_obj, MagicMock(), [])
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.voicemail_handler.time")
    def test_no_messages_plays_beep(self, mock_time) -> None:
        """If message list is empty, should play a beep then end the call."""
        mock_player_cls, _, _, _ = _setup_rtp_mocks()
        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player_cls.return_value = mock_player

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()

        handler._playback_voicemails("call-1", call_obj, MagicMock(), [])
        mock_player.play_beep.assert_called_once_with(frequency=400, duration_ms=500)
        mock_player.stop.assert_called_once()
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.voicemail_handler.time")
    def test_multiple_messages_played_and_marked(self, mock_time) -> None:
        """Multiple messages should be played in order and marked as listened."""
        mock_player_cls, _, _, _ = _setup_rtp_mocks()
        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = True
        mock_player_cls.return_value = mock_player

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        mailbox = MagicMock()

        messages = [
            {"id": "m1", "file_path": "/audio/vm1.wav"},
            {"id": "m2", "file_path": "/audio/vm2.wav"},
        ]

        handler._playback_voicemails("call-1", call_obj, mailbox, messages)

        assert mock_player.play_file.call_count == 2
        assert mailbox.mark_listened.call_count == 2
        mailbox.mark_listened.assert_any_call("m1")
        mailbox.mark_listened.assert_any_call("m2")
        mock_player.stop.assert_called_once()

    @patch("pbx.core.voicemail_handler.time")
    def test_play_file_failure_skips_mark(self, mock_time) -> None:
        """If play_file returns False, the message should not be marked listened."""
        mock_player_cls, _, _, _ = _setup_rtp_mocks()
        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.return_value = False
        mock_player_cls.return_value = mock_player

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        mailbox = MagicMock()

        messages = [{"id": "m1", "file_path": "/audio/vm1.wav"}]

        handler._playback_voicemails("call-1", call_obj, mailbox, messages)
        mailbox.mark_listened.assert_not_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_error_during_playback_ends_call(self, mock_time) -> None:
        """On KeyError/TypeError/ValueError during playback, call should still be ended."""
        mock_player_cls, _, _, _ = _setup_rtp_mocks()
        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player.play_file.side_effect = KeyError("bad key")
        mock_player_cls.return_value = mock_player

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()

        messages = [{"id": "m1", "file_path": "/audio/vm1.wav"}]
        handler._playback_voicemails("call-1", call_obj, MagicMock(), messages)
        pbx.end_call.assert_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_error_ending_call_during_cleanup(self, mock_time) -> None:
        """If end_call raises during cleanup, the error should be logged."""
        pbx = _make_pbx_core()
        pbx.end_call.side_effect = RuntimeError("cannot end")
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.caller_rtp = None

        handler._playback_voicemails("call-1", call_obj, MagicMock(), [])
        pbx.logger.error.assert_called()


# ---------------------------------------------------------------------------
# _voicemail_ivr_session
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVoicemailIVRSession:
    """Tests for _voicemail_ivr_session."""

    @patch("pbx.core.voicemail_handler.time")
    def test_call_ended_before_ivr_starts(self, mock_time) -> None:
        """If call state is ENDED before IVR starts, should return early."""
        from pbx.core.call import CallState

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state = CallState.ENDED

        handler._voicemail_ivr_session("call-1", call_obj, MagicMock(), MagicMock())
        pbx.end_call.assert_not_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_no_caller_rtp_ends_call(self, mock_time) -> None:
        """If caller RTP is None, should end the call."""
        from pbx.core.call import CallState

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state = CallState.CONNECTED
        call_obj.caller_rtp = None

        handler._voicemail_ivr_session("call-1", call_obj, MagicMock(), MagicMock())
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.voicemail_handler.time")
    def test_player_start_failure_ends_call(self, mock_time) -> None:
        """If RTP player fails to start, should end the call."""
        from pbx.core.call import CallState

        mock_player_cls, mock_recorder_cls, mock_dtmf_cls, _ = _setup_rtp_mocks()
        mock_player = MagicMock()
        mock_player.start.return_value = False
        mock_player_cls.return_value = mock_player

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state = CallState.CONNECTED

        handler._voicemail_ivr_session("call-1", call_obj, MagicMock(), MagicMock())
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.voicemail_handler.time")
    def test_recorder_start_failure_ends_call(self, mock_time) -> None:
        """If RTP recorder fails to start, should stop player and end call."""
        from pbx.core.call import CallState

        mock_player_cls, mock_recorder_cls, mock_dtmf_cls, _ = _setup_rtp_mocks()
        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = False
        mock_recorder_cls.return_value = mock_recorder

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state = CallState.CONNECTED

        handler._voicemail_ivr_session("call-1", call_obj, MagicMock(), MagicMock())
        mock_player.stop.assert_called()
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.voicemail_handler.time")
    def test_ivr_hangup_action(self, mock_time) -> None:
        """When IVR returns hangup action, should play goodbye and exit loop."""
        from pbx.core.call import CallState

        mock_player_cls, mock_recorder_cls, _, mock_get_prompt = _setup_rtp_mocks()
        mock_get_prompt.return_value = b"WAV_AUDIO_DATA"

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_recorder.recorded_data = []
        mock_recorder_cls.return_value = mock_recorder

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state = CallState.CONNECTED
        call_obj.dtmf_info_queue = ["#"]

        voicemail_ivr = MagicMock()
        voicemail_ivr.handle_dtmf.side_effect = [
            {"action": "play_prompt", "prompt": "enter_pin"},
            {"action": "hangup"},
        ]

        handler._voicemail_ivr_session("call-1", call_obj, MagicMock(), voicemail_ivr)

        mock_player.stop.assert_called()
        mock_recorder.stop.assert_called()
        pbx.end_call.assert_called_with("call-1")

    @patch("pbx.core.voicemail_handler.time")
    def test_ivr_play_prompt_action(self, mock_time) -> None:
        """When IVR returns play_prompt action, should play the prompt audio."""
        from pbx.core.call import CallState

        mock_player_cls, mock_recorder_cls, _, mock_get_prompt = _setup_rtp_mocks()
        mock_get_prompt.return_value = b"WAV_PROMPT"

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_recorder.recorded_data = []
        mock_recorder_cls.return_value = mock_recorder

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state = CallState.CONNECTED
        call_obj.dtmf_info_queue = ["1"]

        voicemail_ivr = MagicMock()
        voicemail_ivr.state = "MAIN_MENU"
        call_count = 0

        def handle_dtmf_side_effect(digit):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"action": "play_prompt", "prompt": "enter_pin"}
            if call_count == 2:
                call_obj.state = CallState.ENDED
                return {"action": "play_prompt", "prompt": "main_menu"}
            return {"action": "hangup"}

        voicemail_ivr.handle_dtmf.side_effect = handle_dtmf_side_effect

        handler._voicemail_ivr_session("call-1", call_obj, MagicMock(), voicemail_ivr)
        pbx.end_call.assert_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_ivr_exception_logged_and_call_ended(self, mock_time) -> None:
        """On ValueError in IVR session, error should be logged and call ended."""
        from pbx.core.call import CallState

        mock_player_cls, mock_recorder_cls, _, mock_get_prompt = _setup_rtp_mocks()
        mock_get_prompt.side_effect = ValueError("bad prompt")

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_recorder_cls.return_value = mock_recorder

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state = CallState.CONNECTED

        voicemail_ivr = MagicMock()
        voicemail_ivr.handle_dtmf.return_value = {"action": "play_prompt", "prompt": "enter_pin"}

        handler._voicemail_ivr_session("call-1", call_obj, MagicMock(), voicemail_ivr)
        pbx.logger.error.assert_called()
        pbx.end_call.assert_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_ivr_collect_digit_action(self, mock_time) -> None:
        """When IVR returns collect_digit, loop should continue without extra action."""
        from pbx.core.call import CallState

        mock_player_cls, mock_recorder_cls, _, mock_get_prompt = _setup_rtp_mocks()
        mock_get_prompt.return_value = b"WAV_DATA"

        mock_player = MagicMock()
        mock_player.start.return_value = True
        mock_player_cls.return_value = mock_player

        mock_recorder = MagicMock()
        mock_recorder.start.return_value = True
        mock_recorder.recorded_data = []
        mock_recorder_cls.return_value = mock_recorder

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state = CallState.CONNECTED
        call_obj.dtmf_info_queue = ["5"]

        voicemail_ivr = MagicMock()
        voicemail_ivr.state = "PIN_ENTRY"
        call_count = 0

        def handle_dtmf_side_effect(digit):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"action": "play_prompt", "prompt": "enter_pin"}
            if call_count == 2:
                call_obj.state = CallState.ENDED
                return {"action": "collect_digit"}
            return {"action": "hangup"}

        voicemail_ivr.handle_dtmf.side_effect = handle_dtmf_side_effect

        handler._voicemail_ivr_session("call-1", call_obj, MagicMock(), voicemail_ivr)
        pbx.end_call.assert_called()


# ---------------------------------------------------------------------------
# monitor_voicemail_dtmf
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMonitorVoicemailDTMF:
    """Tests for monitor_voicemail_dtmf."""

    @patch("pbx.core.voicemail_handler.time")
    def test_hash_detected_completes_recording(self, mock_time) -> None:
        """When # is detected, should call complete_voicemail_recording."""
        _, _, mock_dtmf_cls, _ = _setup_rtp_mocks()
        mock_detector = MagicMock()
        mock_detector.detect_tone.return_value = "#"
        mock_dtmf_cls.return_value = mock_detector

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()

        recorder = MagicMock()
        recorder.running = True
        recorder.recorded_data = [b"\x80" * 2000]

        with patch.object(handler, "complete_voicemail_recording") as mock_complete:
            handler.monitor_voicemail_dtmf("call-1", call_obj, recorder)
            mock_complete.assert_called_once_with("call-1")

    @patch("pbx.core.voicemail_handler.time")
    def test_non_hash_digit_does_not_complete(self, mock_time) -> None:
        """Non-# digit should not trigger completion."""
        _, _, mock_dtmf_cls, _ = _setup_rtp_mocks()
        mock_detector = MagicMock()
        mock_detector.detect_tone.return_value = "5"
        mock_dtmf_cls.return_value = mock_detector

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state.value = "ended"

        recorder = MagicMock()
        recorder.running = True
        recorder.recorded_data = [b"\x80" * 2000]

        with patch.object(handler, "complete_voicemail_recording") as mock_complete:
            handler.monitor_voicemail_dtmf("call-1", call_obj, recorder)
            mock_complete.assert_not_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_recorder_not_running_exits(self, mock_time) -> None:
        """When recorder.running is False, monitoring loop should exit."""
        _setup_rtp_mocks()

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()

        recorder = MagicMock()
        recorder.running = False
        recorder.recorded_data = []

        with patch.object(handler, "complete_voicemail_recording") as mock_complete:
            handler.monitor_voicemail_dtmf("call-1", call_obj, recorder)
            mock_complete.assert_not_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_error_in_monitoring_logged(self, mock_time) -> None:
        """Errors during monitoring should be logged without raising."""
        _, _, mock_dtmf_cls, _ = _setup_rtp_mocks()
        mock_dtmf_cls.side_effect = ValueError("detector init failed")

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()

        recorder = MagicMock()
        recorder.running = True
        recorder.recorded_data = [b"\x80" * 2000]

        handler.monitor_voicemail_dtmf("call-1", call_obj, recorder)
        pbx.logger.error.assert_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_no_recorded_data_continues(self, mock_time) -> None:
        """When recorded_data is empty, loop should continue without crash."""
        _, _, mock_dtmf_cls, _ = _setup_rtp_mocks()
        mock_detector = MagicMock()
        mock_dtmf_cls.return_value = mock_detector

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state.value = "ended"

        recorder = MagicMock()
        recorder.running = True
        recorder.recorded_data = []

        with patch.object(handler, "complete_voicemail_recording") as mock_complete:
            handler.monitor_voicemail_dtmf("call-1", call_obj, recorder)
            mock_complete.assert_not_called()

    @patch("pbx.core.voicemail_handler.time")
    def test_insufficient_audio_data_skips_detection(self, mock_time) -> None:
        """When audio data is below the threshold, DTMF detection should be skipped."""
        _, _, mock_dtmf_cls, _ = _setup_rtp_mocks()
        mock_detector = MagicMock()
        mock_dtmf_cls.return_value = mock_detector

        pbx = _make_pbx_core()
        handler = VoicemailHandler(pbx)
        call_obj = _make_call()
        call_obj.state.value = "ended"

        recorder = MagicMock()
        recorder.running = True
        recorder.recorded_data = [b"\x80" * 100]

        with patch.object(handler, "complete_voicemail_recording") as mock_complete:
            handler.monitor_voicemail_dtmf("call-1", call_obj, recorder)
            mock_detector.detect_tone.assert_not_called()


# ---------------------------------------------------------------------------
# complete_voicemail_recording
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompleteVoicemailRecording:
    """Tests for complete_voicemail_recording."""

    def test_call_not_found_returns_early(self) -> None:
        """If call_manager.get_call returns None, should log warning and return."""
        pbx = _make_pbx_core()
        pbx.call_manager.get_call.return_value = None
        handler = VoicemailHandler(pbx)

        handler.complete_voicemail_recording("nonexistent-call")
        pbx.logger.warning.assert_called()
        pbx.end_call.assert_not_called()

    def test_no_recorder_ends_call(self) -> None:
        """If call has no voicemail_recorder, should just end the call."""
        pbx = _make_pbx_core()
        call_obj = _make_call()
        call_obj.voicemail_recorder = None
        delattr(call_obj, "voicemail_recorder")
        pbx.call_manager.get_call.return_value = call_obj

        handler = VoicemailHandler(pbx)
        handler.complete_voicemail_recording("call-1")
        pbx.end_call.assert_called_with("call-1")

    def test_with_audio_data_saves_message(self) -> None:
        """When recorder has audio data, should save a voicemail message."""
        pbx = _make_pbx_core()
        call_obj = _make_call()
        recorder = MagicMock()
        recorder.get_recorded_audio.return_value = b"\x00" * 1000
        recorder.get_duration.return_value = 5.0
        call_obj.voicemail_recorder = recorder
        pbx.call_manager.get_call.return_value = call_obj

        handler = VoicemailHandler(pbx)
        handler.complete_voicemail_recording("call-1")

        recorder.stop.assert_called_once()
        pbx._build_wav_file.assert_called_once_with(b"\x00" * 1000)
        pbx.voicemail_system.save_message.assert_called_once_with(
            extension_number=call_obj.to_extension,
            caller_id=call_obj.from_extension,
            audio_data=b"RIFF_WAV_DATA",
            duration=5.0,
        )
        pbx.end_call.assert_called_with("call-1")

    def test_empty_audio_saves_placeholder(self) -> None:
        """When recorder has empty audio, should save a placeholder voicemail."""
        pbx = _make_pbx_core()
        call_obj = _make_call()
        recorder = MagicMock()
        recorder.get_recorded_audio.return_value = b""
        recorder.get_duration.return_value = 0
        call_obj.voicemail_recorder = recorder
        pbx.call_manager.get_call.return_value = call_obj

        handler = VoicemailHandler(pbx)
        handler.complete_voicemail_recording("call-1")

        recorder.stop.assert_called_once()
        pbx.logger.warning.assert_called()
        pbx.voicemail_system.save_message.assert_called_once()
        pbx.end_call.assert_called_with("call-1")

    def test_none_audio_saves_placeholder(self) -> None:
        """When recorder returns None audio, should save a placeholder voicemail."""
        pbx = _make_pbx_core()
        call_obj = _make_call()
        recorder = MagicMock()
        recorder.get_recorded_audio.return_value = None
        recorder.get_duration.return_value = 0
        call_obj.voicemail_recorder = recorder
        pbx.call_manager.get_call.return_value = call_obj

        handler = VoicemailHandler(pbx)
        handler.complete_voicemail_recording("call-1")

        pbx._build_wav_file.assert_called_with(b"")
        pbx.voicemail_system.save_message.assert_called_once()
        pbx.end_call.assert_called_with("call-1")
