#!/usr/bin/env python3
"""
Test WebRTC voicemail access RTP setup
Verifies that WebRTC clients can access voicemail with audio prompts
"""

import unittest
from unittest.mock import MagicMock, patch


from pbx.core.call import Call, CallState
from pbx.features.webrtc import WebRTCGateway


class TestWebRTCVoicemailAccess:
    """Test cases for WebRTC voicemail access"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.config_file = "config.yml"

    def test_webrtc_voicemail_pattern_detection(self) -> None:
        """Test that WebRTC gateway detects voicemail access pattern"""

        # Create mock PBX core
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core._check_dialplan.return_value = True
        mock_pbx_core.call_manager = MagicMock()

        # Create mock call
        mock_call = MagicMock(spec=Call)
        mock_call.state = CallState.RINGING
        mock_call.rtp_ports = [20000, 20001]
        mock_call.caller_rtp = {"address": "127.0.0.1", "port": 10000, "formats": [0, 8]}
        mock_pbx_core.call_manager.create_call.return_value = mock_call

        # Create mock RTP relay
        mock_pbx_core.rtp_relay = MagicMock()
        mock_pbx_core.rtp_relay.allocate_relay.return_value = (20000, 20001)

        # Create mock voicemail system
        mock_voicemail_system = MagicMock()
        mock_mailbox = MagicMock()
        mock_voicemail_system.get_mailbox.return_value = mock_mailbox
        mock_pbx_core.voicemail_system = mock_voicemail_system

        # Create mock CDR system
        mock_pbx_core.cdr_system = MagicMock()

        # Create WebRTC gateway
        gateway = WebRTCGateway(mock_pbx_core)

        # Create mock session
        mock_session = MagicMock()
        mock_session.extension = "1001"
        mock_session.local_sdp = "v=0\r\no=- 123 456 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 10000 RTP/AVP 0 8\r\nc=IN IP4 127.0.0.1\r\n"

        # Create mock signaling server
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        # Mock the thread start
        with patch("threading.Thread") as mock_thread:
            # Initiate call to voicemail
            call_id = gateway.initiate_call(
                session_id="test-session", target_extension="*1001", webrtc_signaling=mock_signaling
            )

            # Verify call was created
            assert call_id is not None, "Call ID should be returned"

            # Verify voicemail attributes were set
            assert mock_call.voicemail_access, "Call should be marked as voicemail access"
            assert (
                mock_call.voicemail_extension == "1001"
            ), "Voicemail extension should be extracted"

            # Verify call was marked as connected
            mock_call.connect.assert_called_once()

            # Verify CDR was started
            mock_pbx_core.cdr_system.start_record.assert_called_once()

            # Verify IVR session thread was started
            mock_thread.assert_called_once()
            thread_call = mock_thread.call_args
            assert thread_call[1]["daemon"], "Thread should be daemon"

            # Verify thread target is the voicemail IVR session
            assert thread_call[1]["target"] == mock_pbx_core._voicemail_ivr_session

            # Verify thread args include call_id, call, mailbox, and ivr
            args = thread_call[1]["args"]
            assert len(args) == 4, "Should have 4 arguments"
            assert args[0] == call_id, "First arg should be call_id"
            assert args[1] == mock_call, "Second arg should be call"
            assert args[2] == mock_mailbox, "Third arg should be mailbox"
            # Fourth arg is the VoicemailIVR instance


    def test_webrtc_voicemail_invalid_pattern(self) -> None:
        """Test that invalid patterns are not treated as voicemail"""

        # Create mock PBX core
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core._check_dialplan.return_value = False

        # Create WebRTC gateway
        gateway = WebRTCGateway(mock_pbx_core)

        # Create mock session
        mock_session = MagicMock()
        mock_session.extension = "1001"

        # Create mock signaling server
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        # Try to initiate call to invalid extension
        call_id = gateway.initiate_call(
            session_id="test-session",
            target_extension="*99",  # Too short, should not match
            webrtc_signaling=mock_signaling,
        )

        # Should fail because dialplan check returns False
        assert call_id is None, "Call should fail for invalid extension"


    def test_webrtc_voicemail_missing_rtp_info(self) -> None:
        """Test that voicemail gracefully handles missing RTP info"""

        # Create mock PBX core
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core._check_dialplan.return_value = True
        mock_pbx_core.call_manager = MagicMock()

        # Create mock call WITHOUT caller_rtp
        mock_call = MagicMock(spec=Call)
        mock_call.state = CallState.RINGING
        mock_call.rtp_ports = [20000, 20001]
        mock_call.caller_rtp = None  # No RTP info
        mock_pbx_core.call_manager.create_call.return_value = mock_call

        # Create mock RTP relay
        mock_pbx_core.rtp_relay = MagicMock()
        mock_pbx_core.rtp_relay.allocate_relay.return_value = (20000, 20001)

        # Create mock voicemail system
        mock_voicemail_system = MagicMock()
        mock_mailbox = MagicMock()
        mock_voicemail_system.get_mailbox.return_value = mock_mailbox
        mock_pbx_core.voicemail_system = mock_voicemail_system

        # Create mock CDR system
        mock_pbx_core.cdr_system = MagicMock()

        # Create WebRTC gateway
        gateway = WebRTCGateway(mock_pbx_core)

        # Create mock session
        mock_session = MagicMock()
        mock_session.extension = "1001"
        mock_session.local_sdp = None  # No SDP

        # Create mock signaling server
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session

        # Initiate call to voicemail
        call_id = gateway.initiate_call(
            session_id="test-session", target_extension="*1001", webrtc_signaling=mock_signaling
        )

        # Call should be created even without RTP info
        assert call_id is not None, "Call should be created"

        # But voicemail attributes should still be set
        assert mock_call.voicemail_access, "Call should be marked as voicemail access"

        # IVR session should not start without RTP info (just logs warning)
        # This is graceful degradation
