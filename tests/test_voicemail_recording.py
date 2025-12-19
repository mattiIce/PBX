#!/usr/bin/env python3
"""
Test voicemail recording functionality
Tests that calls route to voicemail and can record messages
"""
import os
import shutil
import sys
import tempfile
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.core.call import Call, CallState
from pbx.core.pbx import PBXCore
from pbx.rtp.handler import RTPRecorder
from pbx.utils.config import Config


def test_rtp_recorder():
    """Test RTP recorder can start and stop"""
    print("Testing RTP recorder...")

    recorder = RTPRecorder(local_port=12000, call_id="test-call")
    assert recorder.start()

    # Let it run briefly
    time.sleep(0.5)

    recorder.stop()

    # Get duration and audio
    duration = recorder.get_duration()
    audio = recorder.get_recorded_audio()

    assert duration >= 0
    assert audio is not None

    print("✓ RTP recorder works")


def test_wav_file_builder():
    """Test WAV file building"""
    print("Testing WAV file builder...")

    # Create a temp config
    pbx = PBXCore("config.yml")

    # Test with sample audio data
    sample_audio = b"\x00" * 1000  # 1000 bytes of audio
    wav_data = pbx._build_wav_file(sample_audio)

    # Check WAV header is present
    assert wav_data.startswith(b"RIFF")
    assert b"WAVE" in wav_data[:20]
    assert b"fmt " in wav_data[:50]
    assert b"data" in wav_data[:100]

    # Check that audio data is included
    assert len(wav_data) > len(sample_audio)

    print("✓ WAV file builder works")


def test_voicemail_recording_timer():
    """Test that voicemail recording has proper timer setup"""
    print("Testing voicemail recording timer setup...")

    # Create PBX instance
    pbx = PBXCore("config.yml")

    # Create a mock call
    call = Call("test-call-123", "1001", "1002")
    call.start()

    # Set up required attributes
    from pbx.sip.message import SIPMessage
    from pbx.sip.sdp import SDPBuilder

    # Create a mock INVITE
    invite_msg = SIPMessage()
    invite_msg.method = "INVITE"
    invite_msg.set_header("Call-ID", "test-call-123")
    invite_msg.set_header("CSeq", "1 INVITE")
    invite_msg.set_header("From", "<sip:1001@192.168.1.14>")
    invite_msg.set_header("To", "<sip:1002@192.168.1.14>")
    invite_msg.set_header("Via", "SIP/2.0/UDP 192.168.1.100:5060")

    # Set SDP body
    sdp = SDPBuilder.build_audio_sdp("192.168.1.100", 20000, session_id="test-call-123")
    invite_msg.body = sdp

    call.original_invite = invite_msg
    call.caller_addr = ("192.168.1.100", 5060)

    # Parse SDP
    from pbx.sip.sdp import SDPSession

    sdp_obj = SDPSession()
    sdp_obj.parse(sdp)
    call.caller_rtp = sdp_obj.get_audio_info()

    # Allocate RTP ports
    call.rtp_ports = (15000, 15001)

    # Add to call manager
    pbx.call_manager.active_calls[call.call_id] = call

    # Trigger no-answer handler
    pbx._handle_no_answer(call.call_id)

    # Verify call is routed to voicemail
    assert call.routed_to_voicemail

    # Verify recorder was created
    assert hasattr(call, "voicemail_recorder")
    assert call.voicemail_recorder is not None

    # Verify timer was set
    assert hasattr(call, "voicemail_timer")
    assert call.voicemail_timer is not None

    # Clean up
    if hasattr(call, "voicemail_recorder") and call.voicemail_recorder:
        call.voicemail_recorder.stop()
    if hasattr(call, "voicemail_timer") and call.voicemail_timer:
        call.voicemail_timer.cancel()

    pbx.call_manager.active_calls.clear()

    print("✓ Voicemail recording timer setup works")


def test_voicemail_save_on_hangup():
    """Test that voicemail is saved when caller hangs up"""
    print("Testing voicemail save on hangup...")

    # Create temporary directory for voicemail
    temp_dir = tempfile.mkdtemp()

    try:
        # Create PBX instance with temporary voicemail path
        config = Config("config.yml")
        from pbx.features.voicemail import VoicemailSystem

        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)

        # Create a mock call
        call = Call("test-call-456", "1001", "1002")
        call.start()
        call.routed_to_voicemail = True

        # Create a mock recorder with some data
        recorder = RTPRecorder(local_port=15500, call_id="test-call-456")
        recorder.running = True  # Mark as running
        # Add some fake audio data
        recorder.recorded_data = [b"\x00" * 160]  # One packet of audio
        call.voicemail_recorder = recorder

        # Create PBX and set voicemail system
        pbx = PBXCore("config.yml")
        pbx.voicemail_system = vm_system
        pbx.call_manager.active_calls[call.call_id] = call

        # Trigger end_call (simulates BYE)
        pbx.end_call(call.call_id)

        # Check that voicemail was saved
        mailbox = vm_system.get_mailbox("1002")
        messages = mailbox.get_messages()

        assert len(messages) > 0
        assert messages[0]["caller_id"] == "1001"

        print("✓ Voicemail save on hangup works")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_no_answer_answers_call():
    """Test that no-answer handler answers the call instead of sending busy"""
    print("Testing that no-answer answers the call...")

    # Create PBX instance
    pbx = PBXCore("config.yml")

    # Create a mock call
    call = Call("test-call-789", "1001", "1002")
    call.start()

    # Set up required attributes
    from pbx.sip.message import SIPMessage
    from pbx.sip.sdp import SDPBuilder

    # Create a mock INVITE
    invite_msg = SIPMessage()
    invite_msg.method = "INVITE"
    invite_msg.set_header("Call-ID", "test-call-789")
    invite_msg.set_header("CSeq", "1 INVITE")
    invite_msg.set_header("From", "<sip:1001@192.168.1.14>")
    invite_msg.set_header("To", "<sip:1002@192.168.1.14>")
    invite_msg.set_header("Via", "SIP/2.0/UDP 192.168.1.100:5060")

    # Set SDP body
    sdp = SDPBuilder.build_audio_sdp("192.168.1.100", 20000, session_id="test-call-789")
    invite_msg.body = sdp

    call.original_invite = invite_msg
    call.caller_addr = ("192.168.1.100", 5060)

    # Parse SDP
    from pbx.sip.sdp import SDPSession

    sdp_obj = SDPSession()
    sdp_obj.parse(sdp)
    call.caller_rtp = sdp_obj.get_audio_info()

    # Allocate RTP ports
    call.rtp_ports = (15100, 15101)

    # Add to call manager
    pbx.call_manager.active_calls[call.call_id] = call

    # Trigger no-answer handler
    pbx._handle_no_answer(call.call_id)

    # Verify call is connected (answered) not ended
    assert call.state == CallState.CONNECTED

    # Verify call is routed to voicemail
    assert call.routed_to_voicemail

    # Clean up
    if hasattr(call, "voicemail_recorder") and call.voicemail_recorder:
        call.voicemail_recorder.stop()
    if hasattr(call, "voicemail_timer") and call.voicemail_timer:
        call.voicemail_timer.cancel()

    pbx.call_manager.active_calls.clear()

    print("✓ No-answer handler answers the call correctly")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Voicemail Recording Tests")
    print("=" * 60)
    print()

    tests = [
        test_rtp_recorder,
        test_wav_file_builder,
        test_voicemail_recording_timer,
        test_voicemail_save_on_hangup,
        test_no_answer_answers_call,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
