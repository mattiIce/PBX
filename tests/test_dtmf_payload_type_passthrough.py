#!/usr/bin/env python3
"""
Test to verify DTMF payload type is properly passed through to build_audio_sdp

This test verifies the fix for the issue where automatic codec selection was not
working server-side because the dtmf_payload_type parameter was not being passed
to the build_audio_sdp function.
"""

import unittest
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


if __name__ == '__main__':
    unittest.main()
