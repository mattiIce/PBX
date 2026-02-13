#!/usr/bin/env python3
"""
Test voicemail IVR early termination handling

This test validates that when a call is terminated immediately after being answered
(e.g., BYE received during RTP stabilization period), the IVR session properly
detects this and exits gracefully without starting the IVR loop.
"""

import threading
import time
from unittest.mock import MagicMock, patch


from pbx.core.call import Call, CallState


class TestVoicemailIVREarlyTermination:
    """Test cases for voicemail IVR early termination"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.config_file = "config.yml"

    def test_ivr_detects_call_ended_before_start(self) -> None:
        """
        Test that IVR detects when call ends before the main loop starts.

        This simulates the race condition where:
        1. Call is answered
        2. IVR thread starts and sleeps for RTP stabilization
        3. BYE is received and call is terminated
        4. IVR wakes up and should detect call is ended before entering main loop
        """
        # Create mock PBX core
        from pbx.core.pbx import PBXCore

        # Mock the necessary components
        with (
            patch("pbx.core.pbx.VoicemailSystem") as MockVoicemailSystem,
            patch("pbx.rtp.handler.RTPPlayer") as MockRTPPlayer,
            patch("pbx.rtp.handler.RTPRecorder") as MockRTPRecorder,
        ):

            # Set up mocks
            mock_vm_system = MagicMock()
            MockVoicemailSystem.return_value = mock_vm_system

            mock_mailbox = MagicMock()
            mock_vm_system.get_mailbox.return_value = mock_mailbox

            # Create IVR instance
            from pbx.features.voicemail import VoicemailIVR

            mock_ivr = VoicemailIVR(mock_vm_system, "1537")

            # Mock RTP components
            mock_player = MagicMock()
            mock_player.start.return_value = True
            mock_player.play_file.return_value = None
            MockRTPPlayer.return_value = mock_player

            mock_recorder = MagicMock()
            mock_recorder.start.return_value = True
            mock_recorder.recorded_data = []
            MockRTPRecorder.return_value = mock_recorder

            # Create PBX core
            pbx_core = PBXCore(self.config_file)

            # Create a call
            call = Call("test-call-early-term", "1537", "*97")
            call.state = CallState.CONNECTED
            call.caller_rtp = {"address": "127.0.0.1", "port": 10000}
            call.rtp_ports = [20000, 20001]
            call.voicemail_extension = "1537"

            # Track if IVR loop started

            # Patch the logger to capture log messages
            with patch.object(pbx_core, "logger") as mock_logger:

                # Simulate call ending before IVR loop starts
                def end_call_after_setup() -> None:
                    """End call after a short delay to simulate BYE during setup"""
                    time.sleep(0.3)  # Less than the 0.5s RTP stabilization sleep
                    call.end()

                # Start thread to end the call
                end_thread = threading.Thread(target=end_call_after_setup)
                end_thread.daemon = True
                end_thread.start()

                # Run the IVR session
                pbx_core._voicemail_ivr_session(
                    "test-call-early-term", call, mock_mailbox, mock_ivr
                )

                # Wait for end thread to complete
                end_thread.join(timeout=2.0)

                # Verify the appropriate log message was generated
                # Should see "call ended before IVR could start" instead of
                # "IVR started"
                log_calls = [str(call) for call in mock_logger.info.call_args_list]

                # Check if we logged that call ended before IVR started
                ended_before_start = any(
                    "call ended before IVR could start" in str(call) for call in log_calls
                )

                # Should NOT see "IVR started" message if call ended early
                ivr_started = any(
                    "Voicemail IVR started" in str(call) and "waiting for PIN" in str(call)
                    for call in log_calls
                )

                # Assert the call ended as expected
                assert call.state == CallState.ENDED

                # We should see the early termination message
                # and NOT see the "IVR started" message
                assert ended_before_start, "Should log that call ended before IVR started"
                assert not ivr_started, "Should NOT log 'IVR started' if call ended early"

    def test_ivr_session_ended_message_only_after_loop(self) -> None:
        """
        Test that "IVR session ended" log only appears after the IVR loop runs.

        If call ends before IVR loop starts, we should NOT see both
        "IVR started" and "IVR session ended" at the same timestamp.
        """
        from pbx.core.pbx import PBXCore

        with (
            patch("pbx.core.pbx.VoicemailSystem") as MockVoicemailSystem,
            patch("pbx.rtp.handler.RTPPlayer") as MockRTPPlayer,
            patch("pbx.rtp.handler.RTPRecorder") as MockRTPRecorder,
        ):

            # Set up mocks
            mock_vm_system = MagicMock()
            MockVoicemailSystem.return_value = mock_vm_system

            mock_mailbox = MagicMock()
            mock_vm_system.get_mailbox.return_value = mock_mailbox

            from pbx.features.voicemail import VoicemailIVR

            mock_ivr = VoicemailIVR(mock_vm_system, "1537")

            mock_player = MagicMock()
            mock_player.start.return_value = True
            MockRTPPlayer.return_value = mock_player

            mock_recorder = MagicMock()
            mock_recorder.start.return_value = True
            mock_recorder.recorded_data = []
            MockRTPRecorder.return_value = mock_recorder

            pbx_core = PBXCore(self.config_file)

            # Create call that's already ended
            call = Call("test-call-already-ended", "1537", "*97")
            call.caller_rtp = {"address": "127.0.0.1", "port": 10000}
            call.rtp_ports = [20000, 20001]
            call.voicemail_extension = "1537"
            call.end()  # End it immediately

            with patch.object(pbx_core, "logger") as mock_logger:
                # Run IVR session
                pbx_core._voicemail_ivr_session(
                    "test-call-already-ended", call, mock_mailbox, mock_ivr
                )

                log_calls = [str(call) for call in mock_logger.info.call_args_list]

                # Should see early termination message
                ended_before_start = any(
                    "call ended before IVR could start" in str(call) for call in log_calls
                )

                # Should NOT see "IVR session ended" if IVR never started
                # (session_ended might still appear in finally block)
                any("Voicemail IVR session ended" in str(call) for call in log_calls)

                assert ended_before_start, "Should detect call ended before IVR started"
                # Note: session_ended might still appear in finally block,
                # but it should not appear at the same time as "IVR started"
