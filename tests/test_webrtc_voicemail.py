#!/usr/bin/env python3
"""
Test WebRTC voicemail access RTP setup
Verifies that WebRTC clients can access voicemail with audio prompts
"""
import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.webrtc import WebRTCGateway
from pbx.core.call import Call, CallState


class TestWebRTCVoicemailAccess(unittest.TestCase):
    """Test cases for WebRTC voicemail access"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config_file = 'config.yml'
        
    def test_webrtc_voicemail_pattern_detection(self):
        """Test that WebRTC gateway detects voicemail access pattern"""
        print("\nTesting WebRTC voicemail pattern detection...")
        
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
        mock_call.caller_rtp = {
            'address': '127.0.0.1',
            'port': 10000,
            'formats': [0, 8]
        }
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
        mock_session.extension = '1001'
        mock_session.local_sdp = 'v=0\r\no=- 123 456 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 10000 RTP/AVP 0 8\r\nc=IN IP4 127.0.0.1\r\n'
        
        # Create mock signaling server
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session
        
        # Mock the thread start
        with patch('threading.Thread') as mock_thread:
            # Initiate call to voicemail
            call_id = gateway.initiate_call(
                session_id='test-session',
                target_extension='*1001',
                webrtc_signaling=mock_signaling
            )
            
            # Verify call was created
            assert call_id is not None, "Call ID should be returned"
            
            # Verify voicemail attributes were set
            assert mock_call.voicemail_access == True, "Call should be marked as voicemail access"
            assert mock_call.voicemail_extension == '1001', "Voicemail extension should be extracted"
            
            # Verify call was marked as connected
            mock_call.connect.assert_called_once()
            
            # Verify CDR was started
            mock_pbx_core.cdr_system.start_record.assert_called_once()
            
            # Verify IVR session thread was started
            mock_thread.assert_called_once()
            thread_call = mock_thread.call_args
            assert thread_call[1]['daemon'] == True, "Thread should be daemon"
            
            # Verify thread target is the voicemail IVR session
            assert thread_call[1]['target'] == mock_pbx_core._voicemail_ivr_session
            
            # Verify thread args include call_id, call, mailbox, and ivr
            args = thread_call[1]['args']
            assert len(args) == 4, "Should have 4 arguments"
            assert args[0] == call_id, "First arg should be call_id"
            assert args[1] == mock_call, "Second arg should be call"
            assert args[2] == mock_mailbox, "Third arg should be mailbox"
            # Fourth arg is the VoicemailIVR instance
            
        print("✓ WebRTC voicemail pattern detection works")
        
    def test_webrtc_voicemail_invalid_pattern(self):
        """Test that invalid patterns are not treated as voicemail"""
        print("\nTesting invalid voicemail pattern rejection...")
        
        # Create mock PBX core
        mock_pbx_core = MagicMock()
        mock_pbx_core.extension_registry = MagicMock()
        mock_pbx_core.extension_registry.get_extension.return_value = None
        mock_pbx_core._check_dialplan.return_value = False
        
        # Create WebRTC gateway
        gateway = WebRTCGateway(mock_pbx_core)
        
        # Create mock session
        mock_session = MagicMock()
        mock_session.extension = '1001'
        
        # Create mock signaling server
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session
        
        # Try to initiate call to invalid extension
        call_id = gateway.initiate_call(
            session_id='test-session',
            target_extension='*99',  # Too short, should not match
            webrtc_signaling=mock_signaling
        )
        
        # Should fail because dialplan check returns False
        assert call_id is None, "Call should fail for invalid extension"
        
        print("✓ Invalid pattern rejection works")
        
    def test_webrtc_voicemail_missing_rtp_info(self):
        """Test that voicemail gracefully handles missing RTP info"""
        print("\nTesting voicemail with missing RTP info...")
        
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
        mock_session.extension = '1001'
        mock_session.local_sdp = None  # No SDP
        
        # Create mock signaling server
        mock_signaling = MagicMock()
        mock_signaling.get_session.return_value = mock_session
        
        # Initiate call to voicemail
        call_id = gateway.initiate_call(
            session_id='test-session',
            target_extension='*1001',
            webrtc_signaling=mock_signaling
        )
        
        # Call should be created even without RTP info
        assert call_id is not None, "Call should be created"
        
        # But voicemail attributes should still be set
        assert mock_call.voicemail_access == True, "Call should be marked as voicemail access"
        
        # IVR session should not start without RTP info (just logs warning)
        # This is graceful degradation
        
        print("✓ Graceful handling of missing RTP info works")


def run_tests():
    """Run all tests"""
    print("=" * 70)
    print("WebRTC Voicemail Access RTP Setup Tests")
    print("=" * 70)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWebRTCVoicemailAccess)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
