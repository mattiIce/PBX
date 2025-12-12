#!/usr/bin/env python3
"""
Test to verify DTMF payload type is properly passed through to build_audio_sdp

This test verifies the fix for the issue where automatic codec selection was not
working server-side because the dtmf_payload_type parameter was not being passed
to the build_audio_sdp function.
"""

import unittest
from unittest.mock import Mock, MagicMock, call

from pbx.core.pbx import PBXCore
from pbx.sip.sdp import SDPBuilder


class TestDTMFPayloadTypePassthrough(unittest.TestCase):
    """Test DTMF payload type parameter passthrough"""

    def test_dtmf_payload_type_default(self):
        """Test that default DTMF payload type (101) is used when not specified"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.14',
            local_port=10000,
            session_id='test-session'
        )
        
        # Should use default payload type 101
        self.assertIn('m=audio 10000 RTP/AVP 0 8 9 18 2 101', sdp)
        self.assertIn('a=rtpmap:101 telephone-event/8000', sdp)
        self.assertIn('a=fmtp:101 0-16', sdp)

    def test_dtmf_payload_type_custom_96(self):
        """Test that custom DTMF payload type (96) is properly used"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.14',
            local_port=10000,
            session_id='test-session',
            dtmf_payload_type=96
        )
        
        # Should use custom payload type 96
        self.assertIn('m=audio 10000 RTP/AVP 0 8 9 18 2 96', sdp)
        self.assertIn('a=rtpmap:96 telephone-event/8000', sdp)
        self.assertIn('a=fmtp:96 0-16', sdp)
        
        # Should NOT contain 101
        self.assertNotIn('101', sdp)

    def test_dtmf_payload_type_custom_100(self):
        """Test that custom DTMF payload type (100) is properly used"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.14',
            local_port=10000,
            session_id='test-session',
            dtmf_payload_type=100
        )
        
        # Should use custom payload type 100
        self.assertIn('m=audio 10000 RTP/AVP 0 8 9 18 2 100', sdp)
        self.assertIn('a=rtpmap:100 telephone-event/8000', sdp)
        self.assertIn('a=fmtp:100 0-16', sdp)

    def test_dtmf_payload_type_with_custom_codecs(self):
        """Test that DTMF payload type works correctly with custom codec list"""
        # Custom codec list that includes DTMF payload type 102
        custom_codecs = ['0', '8', '102']
        
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.14',
            local_port=10000,
            session_id='test-session',
            codecs=custom_codecs,
            dtmf_payload_type=102
        )
        
        # Should use the custom codec list and payload type
        self.assertIn('m=audio 10000 RTP/AVP 0 8 102', sdp)
        self.assertIn('a=rtpmap:102 telephone-event/8000', sdp)
        self.assertIn('a=fmtp:102 0-16', sdp)

    def test_dtmf_payload_type_with_phone_model_codecs(self):
        """Test DTMF payload type with phone model specific codecs (ZIP37G example)"""
        # ZIP37G uses PCMU/PCMA only with custom DTMF payload
        zip37g_codecs = ['0', '8', '100']
        
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.14',
            local_port=10000,
            session_id='test-session',
            codecs=zip37g_codecs,
            dtmf_payload_type=100
        )
        
        # Should use ZIP37G codecs with correct DTMF payload type
        self.assertIn('m=audio 10000 RTP/AVP 0 8 100', sdp)
        self.assertIn('a=rtpmap:0 PCMU/8000', sdp)
        self.assertIn('a=rtpmap:8 PCMA/8000', sdp)
        self.assertIn('a=rtpmap:100 telephone-event/8000', sdp)
        self.assertIn('a=fmtp:100 0-16', sdp)
        
        # Should NOT have other codecs
        self.assertNotIn('G722', sdp)
        self.assertNotIn('G729', sdp)

    def test_dtmf_payload_type_mismatch_detection(self):
        """Test that DTMF payload type in codec list is used for rtpmap"""
        # Codec list includes 101, and we want to verify it uses what's in the list
        # This is the correct behavior - use what's in the codec list
        codecs_with_101 = ['0', '8', '101']
        
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.14',
            local_port=10000,
            session_id='test-session',
            codecs=codecs_with_101,
            dtmf_payload_type=101  # Matches what's in codec list
        )
        
        # Should have 101 in the media line (from codec list)
        self.assertIn('m=audio 10000 RTP/AVP 0 8 101', sdp)
        
        # Should have rtpmap for 101 since it IS in the codec list
        self.assertIn('a=rtpmap:101 telephone-event/8000', sdp)
        self.assertIn('a=fmtp:101 0-16', sdp)


class TestDTMFPayloadTypeIntegration(unittest.TestCase):
    """Test DTMF payload type integration with PBX configuration"""

    def test_get_dtmf_payload_type_from_config(self):
        """Test that _get_dtmf_payload_type() correctly reads from config"""
        # Create a mock config
        mock_config = Mock()
        mock_config.get.return_value = 100  # Return custom payload type
        
        # Create a minimal PBX instance with just the method we need
        pbx = Mock(spec=PBXCore)
        pbx.config = mock_config
        # Bind the actual method to our mock
        pbx._get_dtmf_payload_type = PBXCore._get_dtmf_payload_type.__get__(pbx)
        
        # Test the method
        payload_type = pbx._get_dtmf_payload_type()
        
        # Verify it requested the correct config key
        mock_config.get.assert_called_once_with('features.dtmf.payload_type', 101)
        # Verify it returned the configured value
        self.assertEqual(payload_type, 100)

    def test_get_dtmf_payload_type_default(self):
        """Test that _get_dtmf_payload_type() returns default when not configured"""
        # Create a mock config that returns the default
        mock_config = Mock()
        mock_config.get.return_value = 101  # Return default payload type
        
        # Create a minimal PBX instance
        pbx = Mock(spec=PBXCore)
        pbx.config = mock_config
        pbx._get_dtmf_payload_type = PBXCore._get_dtmf_payload_type.__get__(pbx)
        
        # Test the method
        payload_type = pbx._get_dtmf_payload_type()
        
        # Verify it returned the default value
        self.assertEqual(payload_type, 101)

    def test_get_codecs_for_phone_model_uses_same_config_key(self):
        """Test that _get_codecs_for_phone_model() uses same config key"""
        # Create a mock config
        mock_config = Mock()
        mock_config.get.return_value = 100  # Custom DTMF payload type
        
        # Create a minimal PBX instance
        pbx = Mock(spec=PBXCore)
        pbx.config = mock_config
        pbx.logger = MagicMock()
        # Bind the actual methods to our mock
        pbx._get_codecs_for_phone_model = PBXCore._get_codecs_for_phone_model.__get__(pbx)
        pbx._get_dtmf_payload_type = PBXCore._get_dtmf_payload_type.__get__(pbx)
        
        # Test _get_codecs_for_phone_model for ZIP37G
        codecs = pbx._get_codecs_for_phone_model('ZIP37G', ['0', '8', '9', '101'])
        
        # Verify it called config.get with the correct key
        # Should have called for 'features.dtmf.payload_type'
        mock_config.get.assert_called_with('features.dtmf.payload_type', 101)
        
        # Verify the codec list includes the custom DTMF payload type
        self.assertIn('100', codecs)
        self.assertEqual(codecs, ['0', '8', '100'])

    def test_dtmf_payload_type_end_to_end(self):
        """Test end-to-end flow from config to SDP generation through _get_dtmf_payload_type()"""
        # Create a mock config with custom DTMF payload type
        mock_config = Mock()
        
        def mock_get(key, default=None):
            if key == 'features.dtmf.payload_type':
                return 100  # Custom payload type
            return default
        
        mock_config.get = mock_get
        
        # Create a minimal PBX instance
        pbx = Mock(spec=PBXCore)
        pbx.config = mock_config
        pbx._get_dtmf_payload_type = PBXCore._get_dtmf_payload_type.__get__(pbx)
        
        # Get the DTMF payload type through the helper method
        dtmf_payload_type = pbx._get_dtmf_payload_type()
        
        # Verify we got the custom value
        self.assertEqual(dtmf_payload_type, 100)
        
        # Now use it to build SDP (simulating what happens in route_call, etc.)
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.14',
            local_port=10000,
            session_id='test-session',
            dtmf_payload_type=dtmf_payload_type
        )
        
        # Verify the SDP contains the custom payload type
        self.assertIn('m=audio 10000 RTP/AVP 0 8 9 18 2 100', sdp)
        self.assertIn('a=rtpmap:100 telephone-event/8000', sdp)
        self.assertIn('a=fmtp:100 0-16', sdp)
        # Should NOT contain the default 101
        self.assertNotIn('101', sdp)

    def test_config_key_consistency(self):
        """Test that both methods use 'features.dtmf.payload_type' config key"""
        # Create a mock config that tracks all get() calls
        mock_config = Mock()
        mock_config.get.return_value = 102
        
        # Create a minimal PBX instance
        pbx = Mock(spec=PBXCore)
        pbx.config = mock_config
        pbx.logger = MagicMock()
        pbx._get_codecs_for_phone_model = PBXCore._get_codecs_for_phone_model.__get__(pbx)
        pbx._get_dtmf_payload_type = PBXCore._get_dtmf_payload_type.__get__(pbx)
        
        # Call both methods
        payload_type = pbx._get_dtmf_payload_type()
        codecs = pbx._get_codecs_for_phone_model('ZIP33G', ['0', '8', '9', '18', '2', '101'])
        
        # Verify both methods used the same config key
        expected_calls = [
            call('features.dtmf.payload_type', 101),  # From _get_dtmf_payload_type
            call('features.dtmf.payload_type', 101),  # From _get_codecs_for_phone_model
        ]
        mock_config.get.assert_has_calls(expected_calls, any_order=True)
        
        # Verify both returned/used the same value
        self.assertEqual(payload_type, 102)
        self.assertIn('102', codecs)


if __name__ == '__main__':
    unittest.main()
