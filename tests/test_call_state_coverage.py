"""Comprehensive tests for pbx/core/call.py - Call state machine."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.core.call import Call, CallManager, CallState


@pytest.mark.unit
class TestCallState:
    """Tests for CallState enum."""

    def test_idle_state_value(self) -> None:
        assert CallState.IDLE.value == "idle"

    def test_calling_state_value(self) -> None:
        assert CallState.CALLING.value == "calling"

    def test_ringing_state_value(self) -> None:
        assert CallState.RINGING.value == "ringing"

    def test_connected_state_value(self) -> None:
        assert CallState.CONNECTED.value == "connected"

    def test_hold_state_value(self) -> None:
        assert CallState.HOLD.value == "hold"

    def test_transferring_state_value(self) -> None:
        assert CallState.TRANSFERRING.value == "transferring"

    def test_ended_state_value(self) -> None:
        assert CallState.ENDED.value == "ended"

    def test_all_states_count(self) -> None:
        assert len(CallState) == 7


@pytest.mark.unit
class TestCallInit:
    """Tests for Call.__init__."""

    def test_basic_attributes(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.call_id == "call-1"
        assert call.from_extension == "1001"
        assert call.to_extension == "1002"

    def test_initial_state_is_idle(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.state == CallState.IDLE

    def test_initial_times_are_none(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.start_time is None
        assert call.answer_time is None
        assert call.end_time is None

    def test_initial_rtp_ports_none(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.rtp_ports is None

    def test_initial_recording_false(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.recording is False

    def test_initial_on_hold_false(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.on_hold is False

    def test_initial_rtp_endpoints_none(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.caller_rtp is None
        assert call.caller_addr is None
        assert call.callee_rtp is None
        assert call.callee_addr is None

    def test_initial_invite_none(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.original_invite is None

    def test_initial_no_answer_timer_none(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.no_answer_timer is None

    def test_initial_routed_to_voicemail_false(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.routed_to_voicemail is False

    def test_initial_transfer_attributes(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.transferred is False
        assert call.transfer_destination is None

    def test_initial_voicemail_attributes(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.voicemail_access is False
        assert call.voicemail_extension is None
        assert call.voicemail_ivr is None

    def test_initial_auto_attendant_attributes(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.auto_attendant_active is False
        assert call.aa_session is None

    def test_initial_dtmf_queue_empty(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.dtmf_info_queue == []


@pytest.mark.unit
class TestCallStart:
    """Tests for Call.start."""

    def test_start_sets_calling_state(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        assert call.state == CallState.CALLING

    def test_start_sets_start_time(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        assert call.start_time is not None
        assert isinstance(call.start_time, datetime)

    def test_start_time_is_utc(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        assert call.start_time.tzinfo is not None


@pytest.mark.unit
class TestCallRing:
    """Tests for Call.ring."""

    def test_ring_sets_ringing_state(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.ring()
        assert call.state == CallState.RINGING


@pytest.mark.unit
class TestCallConnect:
    """Tests for Call.connect."""

    def test_connect_sets_connected_state(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.ring()
        call.connect()
        assert call.state == CallState.CONNECTED

    def test_connect_sets_answer_time(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.ring()
        call.connect()
        assert call.answer_time is not None
        assert isinstance(call.answer_time, datetime)


@pytest.mark.unit
class TestCallHold:
    """Tests for Call.hold."""

    def test_hold_sets_hold_state(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()
        call.hold()
        assert call.state == CallState.HOLD

    def test_hold_sets_on_hold_flag(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()
        call.hold()
        assert call.on_hold is True


@pytest.mark.unit
class TestCallResume:
    """Tests for Call.resume."""

    def test_resume_sets_connected_state(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()
        call.hold()
        call.resume()
        assert call.state == CallState.CONNECTED

    def test_resume_clears_on_hold_flag(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()
        call.hold()
        call.resume()
        assert call.on_hold is False


@pytest.mark.unit
class TestCallEnd:
    """Tests for Call.end."""

    def test_end_sets_ended_state(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()
        call.end()
        assert call.state == CallState.ENDED

    def test_end_sets_end_time(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()
        call.end()
        assert call.end_time is not None
        assert isinstance(call.end_time, datetime)


@pytest.mark.unit
class TestCallGetDuration:
    """Tests for Call.get_duration."""

    def test_duration_zero_when_not_started(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.get_duration() == 0

    def test_duration_positive_when_started(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        # The duration should be >= 0 since start_time was just set
        assert call.get_duration() >= 0

    def test_duration_with_ended_call(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()
        call.end()
        duration = call.get_duration()
        assert duration >= 0

    def test_duration_uses_end_time_when_ended(self) -> None:
        call = Call("call-1", "1001", "1002")
        fixed_start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        fixed_end = datetime(2025, 1, 1, 12, 5, 0, tzinfo=UTC)
        call.start_time = fixed_start
        call.end_time = fixed_end
        assert call.get_duration() == 300.0

    def test_duration_uses_now_when_still_active(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        # No end_time set -> uses datetime.now(UTC)
        duration = call.get_duration()
        assert duration > 0


@pytest.mark.unit
class TestCallStr:
    """Tests for Call.__str__."""

    def test_str_format(self) -> None:
        call = Call("call-1", "1001", "1002")
        result = str(call)
        assert result == "Call call-1: 1001 -> 1002 (idle)"

    def test_str_after_connect(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()
        result = str(call)
        assert "(connected)" in result

    def test_str_after_end(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.end()
        result = str(call)
        assert "(ended)" in result


@pytest.mark.unit
class TestCallStateTransitions:
    """Tests for full call lifecycle state transitions."""

    def test_full_call_lifecycle(self) -> None:
        call = Call("call-1", "1001", "1002")
        assert call.state == CallState.IDLE

        call.start()
        assert call.state == CallState.CALLING

        call.ring()
        assert call.state == CallState.RINGING

        call.connect()
        assert call.state == CallState.CONNECTED

        call.hold()
        assert call.state == CallState.HOLD

        call.resume()
        assert call.state == CallState.CONNECTED

        call.end()
        assert call.state == CallState.ENDED

    def test_hold_resume_cycle(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.start()
        call.connect()

        call.hold()
        assert call.on_hold is True
        call.resume()
        assert call.on_hold is False
        call.hold()
        assert call.on_hold is True
        call.resume()
        assert call.on_hold is False


@pytest.mark.unit
class TestCallManagerInit:
    """Tests for CallManager.__init__."""

    def test_initial_active_calls_empty(self) -> None:
        mgr = CallManager()
        assert mgr.active_calls == {}

    def test_initial_call_history_empty(self) -> None:
        mgr = CallManager()
        assert mgr.call_history == []


@pytest.mark.unit
class TestCallManagerCreateCall:
    """Tests for CallManager.create_call."""

    def test_create_call_returns_call_object(self) -> None:
        mgr = CallManager()
        call = mgr.create_call("call-1", "1001", "1002")
        assert isinstance(call, Call)
        assert call.call_id == "call-1"
        assert call.from_extension == "1001"
        assert call.to_extension == "1002"

    def test_create_call_adds_to_active(self) -> None:
        mgr = CallManager()
        call = mgr.create_call("call-1", "1001", "1002")
        assert "call-1" in mgr.active_calls
        assert mgr.active_calls["call-1"] is call

    def test_create_multiple_calls(self) -> None:
        mgr = CallManager()
        mgr.create_call("call-1", "1001", "1002")
        mgr.create_call("call-2", "1003", "1004")
        assert len(mgr.active_calls) == 2


@pytest.mark.unit
class TestCallManagerGetCall:
    """Tests for CallManager.get_call."""

    def test_get_existing_call(self) -> None:
        mgr = CallManager()
        call = mgr.create_call("call-1", "1001", "1002")
        result = mgr.get_call("call-1")
        assert result is call

    def test_get_nonexistent_call_returns_none(self) -> None:
        mgr = CallManager()
        result = mgr.get_call("no-such-call")
        assert result is None


@pytest.mark.unit
class TestCallManagerEndCall:
    """Tests for CallManager.end_call."""

    def test_end_existing_call_returns_true(self) -> None:
        mgr = CallManager()
        mgr.create_call("call-1", "1001", "1002")
        result = mgr.end_call("call-1")
        assert result is True

    def test_end_call_removes_from_active(self) -> None:
        mgr = CallManager()
        mgr.create_call("call-1", "1001", "1002")
        mgr.end_call("call-1")
        assert "call-1" not in mgr.active_calls

    def test_end_call_adds_to_history(self) -> None:
        mgr = CallManager()
        call = mgr.create_call("call-1", "1001", "1002")
        mgr.end_call("call-1")
        assert len(mgr.call_history) == 1
        assert mgr.call_history[0] is call

    def test_end_call_sets_ended_state(self) -> None:
        mgr = CallManager()
        call = mgr.create_call("call-1", "1001", "1002")
        mgr.end_call("call-1")
        assert call.state == CallState.ENDED
        assert call.end_time is not None

    def test_end_nonexistent_call_returns_false(self) -> None:
        mgr = CallManager()
        result = mgr.end_call("no-such-call")
        assert result is False


@pytest.mark.unit
class TestCallManagerGetActiveCalls:
    """Tests for CallManager.get_active_calls."""

    def test_no_active_calls(self) -> None:
        mgr = CallManager()
        assert mgr.get_active_calls() == []

    def test_returns_all_active_calls(self) -> None:
        mgr = CallManager()
        mgr.create_call("call-1", "1001", "1002")
        mgr.create_call("call-2", "1003", "1004")
        active = mgr.get_active_calls()
        assert len(active) == 2

    def test_returns_list_copy(self) -> None:
        mgr = CallManager()
        mgr.create_call("call-1", "1001", "1002")
        active = mgr.get_active_calls()
        assert isinstance(active, list)
        # Modifying the returned list should not affect internal state
        active.clear()
        assert len(mgr.active_calls) == 1


@pytest.mark.unit
class TestCallManagerGetExtensionCalls:
    """Tests for CallManager.get_extension_calls."""

    def test_no_calls_for_extension(self) -> None:
        mgr = CallManager()
        mgr.create_call("call-1", "1001", "1002")
        result = mgr.get_extension_calls("9999")
        assert result == []

    def test_find_call_by_from_extension(self) -> None:
        mgr = CallManager()
        call = mgr.create_call("call-1", "1001", "1002")
        result = mgr.get_extension_calls("1001")
        assert len(result) == 1
        assert result[0] is call

    def test_find_call_by_to_extension(self) -> None:
        mgr = CallManager()
        call = mgr.create_call("call-1", "1001", "1002")
        result = mgr.get_extension_calls("1002")
        assert len(result) == 1
        assert result[0] is call

    def test_find_multiple_calls_for_extension(self) -> None:
        mgr = CallManager()
        mgr.create_call("call-1", "1001", "1002")
        mgr.create_call("call-2", "1001", "1003")
        result = mgr.get_extension_calls("1001")
        assert len(result) == 2

    def test_extension_both_caller_and_callee(self) -> None:
        mgr = CallManager()
        mgr.create_call("call-1", "1001", "1002")
        mgr.create_call("call-2", "1003", "1001")
        result = mgr.get_extension_calls("1001")
        assert len(result) == 2


@pytest.mark.unit
class TestCallMutableAttributes:
    """Tests for setting mutable attributes on Call objects."""

    def test_set_rtp_ports(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.rtp_ports = (10000, 10002)
        assert call.rtp_ports == (10000, 10002)

    def test_set_recording(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.recording = True
        assert call.recording is True

    def test_set_caller_rtp_info(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.caller_rtp = {"port": 10000, "ip": "192.168.1.100"}
        assert call.caller_rtp["port"] == 10000

    def test_set_callee_rtp_info(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.callee_rtp = {"port": 10002, "ip": "192.168.1.101"}
        assert call.callee_rtp["port"] == 10002

    def test_set_caller_addr(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.caller_addr = ("192.168.1.100", 5060)
        assert call.caller_addr == ("192.168.1.100", 5060)

    def test_set_callee_addr(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.callee_addr = ("192.168.1.101", 5060)
        assert call.callee_addr == ("192.168.1.101", 5060)

    def test_set_transfer_attributes(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.transferred = True
        call.transfer_destination = "1005"
        assert call.transferred is True
        assert call.transfer_destination == "1005"

    def test_set_voicemail_attributes(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.voicemail_access = True
        call.voicemail_extension = "1001"
        call.voicemail_ivr = MagicMock()
        assert call.voicemail_access is True
        assert call.voicemail_extension == "1001"
        assert call.voicemail_ivr is not None

    def test_set_auto_attendant_attributes(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.auto_attendant_active = True
        call.aa_session = {"menu": "main", "retries": 0}
        assert call.auto_attendant_active is True
        assert call.aa_session["menu"] == "main"

    def test_set_dtmf_queue(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.dtmf_info_queue.append("1")
        call.dtmf_info_queue.append("2")
        assert call.dtmf_info_queue == ["1", "2"]

    def test_set_original_invite(self) -> None:
        call = Call("call-1", "1001", "1002")
        mock_invite = MagicMock()
        call.original_invite = mock_invite
        assert call.original_invite is mock_invite

    def test_set_no_answer_timer(self) -> None:
        call = Call("call-1", "1001", "1002")
        mock_timer = MagicMock()
        call.no_answer_timer = mock_timer
        assert call.no_answer_timer is mock_timer

    def test_set_routed_to_voicemail(self) -> None:
        call = Call("call-1", "1001", "1002")
        call.routed_to_voicemail = True
        assert call.routed_to_voicemail is True
