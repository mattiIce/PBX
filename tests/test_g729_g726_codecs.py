"""
Tests for G.729 and G.726 codec support
Validates codec initialization, SDP generation, and framework functionality
"""
import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.g729_codec import G729Codec, G729CodecManager
from pbx.features.g726_codec import G726Codec, G726CodecManager
from pbx.sip.sdp import SDPBuilder, SDPSession


class TestG729Codec(unittest.TestCase):
    """Test G.729 codec functionality"""
    
    def test_g729_initialization(self):
        """Test G.729 codec initialization"""
        codec = G729Codec(variant='G729AB')
        self.assertEqual(codec.variant, 'G729AB')
        self.assertEqual(codec.SAMPLE_RATE, 8000)
        self.assertEqual(codec.PAYLOAD_TYPE, 18)
        self.assertEqual(codec.BITRATE, 8000)
    
    def test_g729_info(self):
        """Test G.729 codec info retrieval"""
        codec = G729Codec(variant='G729A')
        info = codec.get_info()
        
        self.assertEqual(info['name'], 'G.729')
        self.assertEqual(info['variant'], 'G729A')
        self.assertEqual(info['sample_rate'], 8000)
        self.assertEqual(info['bitrate'], 8000)
        self.assertEqual(info['payload_type'], 18)
        self.assertTrue(info['license_required'])
    
    def test_g729_sdp_description(self):
        """Test G.729 SDP format string"""
        codec = G729Codec()
        sdp_desc = codec.get_sdp_description()
        
        self.assertIn('rtpmap:18', sdp_desc)
        self.assertIn('G729/8000', sdp_desc)
    
    def test_g729_fmtp_params(self):
        """Test G.729 FMTP parameters"""
        # Base variant should disable Annex B
        codec_base = G729Codec(variant='G729')
        fmtp = codec_base.get_fmtp_params()
        self.assertIsNotNone(fmtp)
        self.assertIn('annexb=no', fmtp)
        
        # AB variant should not have fmtp
        codec_ab = G729Codec(variant='G729AB')
        fmtp_ab = codec_ab.get_fmtp_params()
        self.assertIsNone(fmtp_ab)
    
    def test_g729_capabilities(self):
        """Test G.729 capabilities"""
        caps = G729Codec.get_capabilities()
        
        self.assertIn('G729AB', caps['variants'])
        self.assertEqual(caps['sample_rate'], 8000)
        self.assertEqual(caps['bitrate'], 8000)
        self.assertEqual(caps['channels'], 1)


class TestG729CodecManager(unittest.TestCase):
    """Test G.729 codec manager"""
    
    def test_manager_initialization(self):
        """Test codec manager initialization"""
        config = {'codecs.g729.enabled': True, 'codecs.g729.variant': 'G729A'}
        manager = G729CodecManager(config)
        
        self.assertTrue(manager.enabled)
        self.assertEqual(manager.variant, 'G729A')
    
    def test_manager_create_encoder(self):
        """Test creating encoder"""
        config = {'codecs.g729.enabled': True}
        manager = G729CodecManager(config)
        
        encoder = manager.create_encoder('call123')
        self.assertIsNotNone(encoder)
        self.assertIsInstance(encoder, G729Codec)
        
        # Should be retrievable
        retrieved = manager.get_encoder('call123')
        self.assertEqual(encoder, retrieved)
    
    def test_manager_disabled(self):
        """Test manager when disabled"""
        config = {'codecs.g729.enabled': False}
        manager = G729CodecManager(config)
        
        encoder = manager.create_encoder('call123')
        self.assertIsNone(encoder)
    
    def test_manager_release_codec(self):
        """Test releasing codec resources"""
        config = {'codecs.g729.enabled': True}
        manager = G729CodecManager(config)
        
        manager.create_encoder('call123')
        manager.create_decoder('call123')
        
        manager.release_codec('call123')
        
        self.assertIsNone(manager.get_encoder('call123'))
        self.assertIsNone(manager.get_decoder('call123'))
    
    def test_manager_sdp_capabilities(self):
        """Test SDP capabilities"""
        config = {'codecs.g729.enabled': True}
        manager = G729CodecManager(config)
        
        caps = manager.get_sdp_capabilities()
        self.assertTrue(len(caps) > 0)
        self.assertTrue(any('rtpmap:18' in cap for cap in caps))


class TestG726Codec(unittest.TestCase):
    """Test G.726 codec functionality"""
    
    def test_g726_initialization_32k(self):
        """Test G.726-32 initialization"""
        codec = G726Codec(bitrate=32000)
        self.assertEqual(codec.bitrate, 32000)
        self.assertEqual(codec.bitrate_kbps, 32)
        self.assertEqual(codec.bits_per_sample, 4)
        self.assertEqual(codec.payload_type, 2)  # Static type for G.726-32
    
    def test_g726_initialization_40k(self):
        """Test G.726-40 initialization"""
        codec = G726Codec(bitrate=40000)
        self.assertEqual(codec.bitrate, 40000)
        self.assertEqual(codec.bitrate_kbps, 40)
        self.assertEqual(codec.bits_per_sample, 5)
        self.assertEqual(codec.payload_type, 114)  # Dynamic type
    
    def test_g726_invalid_bitrate(self):
        """Test invalid bitrate raises error"""
        with self.assertRaises(ValueError):
            G726Codec(bitrate=48000)
    
    def test_g726_info(self):
        """Test G.726 codec info"""
        codec = G726Codec(bitrate=32000)
        info = codec.get_info()
        
        self.assertEqual(info['name'], 'G.726-32')
        self.assertEqual(info['sample_rate'], 8000)
        self.assertEqual(info['bitrate'], 32000)
        self.assertEqual(info['bits_per_sample'], 4)
        self.assertEqual(info['payload_type'], 2)
    
    def test_g726_sdp_description(self):
        """Test G.726 SDP format strings"""
        codec_32 = G726Codec(bitrate=32000)
        sdp_32 = codec_32.get_sdp_description()
        self.assertIn('rtpmap:2', sdp_32)
        self.assertIn('G726-32/8000', sdp_32)
        
        codec_24 = G726Codec(bitrate=24000)
        sdp_24 = codec_24.get_sdp_description()
        self.assertIn('G726-24/8000', sdp_24)
    
    def test_g726_capabilities(self):
        """Test G.726 capabilities"""
        caps = G726Codec.get_capabilities()
        
        self.assertIn(32000, caps['bitrates'])
        self.assertIn(24000, caps['bitrates'])
        self.assertIn(16000, caps['bitrates'])
        self.assertIn(40000, caps['bitrates'])
        self.assertEqual(caps['sample_rate'], 8000)
    
    def test_g726_is_supported(self):
        """Test G.726 support detection"""
        # G.726-32 should be supported via audioop
        # Other bitrates need specialized library
        supported_32 = G726Codec.is_supported(32000)
        # We can't guarantee audioop is available in all environments
        # but we can check the method works
        self.assertIsInstance(supported_32, bool)


class TestG726CodecManager(unittest.TestCase):
    """Test G.726 codec manager"""
    
    def test_manager_initialization(self):
        """Test codec manager initialization"""
        config = {'codecs.g726.enabled': True, 'codecs.g726.bitrate': 32000}
        manager = G726CodecManager(config)
        
        self.assertTrue(manager.enabled)
        self.assertEqual(manager.default_bitrate, 32000)
    
    def test_manager_invalid_bitrate(self):
        """Test manager handles invalid bitrate"""
        config = {'codecs.g726.enabled': True, 'codecs.g726.bitrate': 99999}
        manager = G726CodecManager(config)
        
        # Should default to 32000
        self.assertEqual(manager.default_bitrate, 32000)
    
    def test_manager_create_encoder(self):
        """Test creating encoder"""
        config = {'codecs.g726.enabled': True}
        manager = G726CodecManager(config)
        
        encoder = manager.create_encoder('call456', bitrate=24000)
        self.assertIsNotNone(encoder)
        self.assertIsInstance(encoder, G726Codec)
        self.assertEqual(encoder.bitrate, 24000)
    
    def test_manager_statistics(self):
        """Test manager statistics"""
        config = {'codecs.g726.enabled': True, 'codecs.g726.bitrate': 32000}
        manager = G726CodecManager(config)
        
        manager.create_encoder('call1')
        manager.create_decoder('call2')
        
        stats = manager.get_statistics()
        self.assertTrue(stats['enabled'])
        self.assertEqual(stats['default_bitrate'], 32000)
        self.assertEqual(stats['active_encoders'], 1)
        self.assertEqual(stats['active_decoders'], 1)


class TestSDPWithNewCodecs(unittest.TestCase):
    """Test SDP generation with G.729 and G.726"""
    
    def test_sdp_with_g729(self):
        """Test SDP includes G.729"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.100',
            local_port=10000,
            codecs=['0', '18', '101']  # PCMU, G.729, telephone-event
        )
        
        self.assertIn('m=audio 10000', sdp)
        self.assertIn('0 18 101', sdp)  # Payload types in m= line
        self.assertIn('a=rtpmap:0 PCMU/8000', sdp)
        self.assertIn('a=rtpmap:18 G729/8000', sdp)
        self.assertIn('a=rtpmap:101 telephone-event/8000', sdp)
    
    def test_sdp_with_g726_32(self):
        """Test SDP includes G.726-32"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.100',
            local_port=10000,
            codecs=['0', '2', '101']  # PCMU, G.726-32, telephone-event
        )
        
        self.assertIn('0 2 101', sdp)
        self.assertIn('a=rtpmap:2 G726-32/8000', sdp)
    
    def test_sdp_with_g726_variants(self):
        """Test SDP includes G.726 variants"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.100',
            local_port=10000,
            codecs=['0', '112', '113', '114', '101']  # PCMU, G.726 variants, DTMF
        )
        
        self.assertIn('a=rtpmap:112 G726-16/8000', sdp)
        self.assertIn('a=rtpmap:113 G726-24/8000', sdp)
        self.assertIn('a=rtpmap:114 G726-40/8000', sdp)
    
    def test_sdp_default_includes_new_codecs(self):
        """Test default SDP includes G.729 and G.726-32"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip='192.168.1.100',
            local_port=10000
            # Using default codecs
        )
        
        # Default should now include: 0, 8, 9, 18, 2, 101
        self.assertIn('a=rtpmap:0 PCMU/8000', sdp)
        self.assertIn('a=rtpmap:8 PCMA/8000', sdp)
        self.assertIn('a=rtpmap:9 G722/8000', sdp)
        self.assertIn('a=rtpmap:18 G729/8000', sdp)
        self.assertIn('a=rtpmap:2 G726-32/8000', sdp)
        self.assertIn('a=rtpmap:101 telephone-event/8000', sdp)
    
    def test_sdp_parsing_preserves_new_codecs(self):
        """Test SDP parser handles new codecs"""
        sdp_text = """v=0
o=pbx 12345 0 IN IP4 192.168.1.100
s=PBX Call
c=IN IP4 192.168.1.100
t=0 0
m=audio 10000 RTP/AVP 0 18 2 101
a=rtpmap:0 PCMU/8000
a=rtpmap:18 G729/8000
a=rtpmap:2 G726-32/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=sendrecv
"""
        
        session = SDPSession()
        session.parse(sdp_text)
        
        audio_info = session.get_audio_info()
        self.assertIsNotNone(audio_info)
        self.assertEqual(audio_info['port'], 10000)
        self.assertIn('0', audio_info['formats'])
        self.assertIn('18', audio_info['formats'])
        self.assertIn('2', audio_info['formats'])


if __name__ == '__main__':
    unittest.main()
