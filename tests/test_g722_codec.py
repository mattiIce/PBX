"""
Tests for G.722 HD Audio Codec
"""
import unittest
from pbx.features.g722_codec import G722Codec, G722CodecManager


class TestG722Codec(unittest.TestCase):
    """Test G.722 codec functionality"""
    
    def test_codec_initialization(self):
        """Test codec initialization"""
        codec = G722Codec()
        
        self.assertIsNotNone(codec)
        self.assertEqual(codec.SAMPLE_RATE, 16000)
        self.assertEqual(codec.PAYLOAD_TYPE, 9)
    
    def test_codec_info(self):
        """Test codec information"""
        codec = G722Codec(bitrate=G722Codec.MODE_64K)
        info = codec.get_info()
        
        self.assertEqual(info['name'], 'G.722')
        self.assertEqual(info['sample_rate'], 16000)
        self.assertEqual(info['bitrate'], 64000)
        self.assertEqual(info['payload_type'], 9)
    
    def test_encode_stub(self):
        """Test encoding"""
        codec = G722Codec()
        
        # Create fake PCM data (16-bit, 16kHz, 20ms = 320 samples = 640 bytes)
        pcm_data = b'\x00' * 640
        
        encoded = codec.encode(pcm_data)
        
        self.assertIsNotNone(encoded)
        # G.722 encodes 2 samples (4 bytes) into 1 byte, so 640 bytes -> 160 bytes
        self.assertEqual(len(encoded), len(pcm_data) // 4)
    
    def test_decode_stub(self):
        """Test decoding"""
        codec = G722Codec()
        
        # Create fake G.722 data
        g722_data = b'\x00' * 320
        
        decoded = codec.decode(g722_data)
        
        self.assertIsNotNone(decoded)
        # Each G.722 byte decodes to 2 samples (4 bytes), so 320 bytes -> 1280 bytes
        self.assertEqual(len(decoded), len(g722_data) * 4)
    
    def test_sdp_description(self):
        """Test SDP description generation"""
        codec = G722Codec()
        sdp = codec.get_sdp_description()
        
        self.assertIn('G722', sdp)
        self.assertIn('16000', sdp)
        self.assertIn('9', sdp)
    
    def test_is_supported(self):
        """Test codec support check"""
        supported = G722Codec.is_supported()
        self.assertTrue(supported)
    
    def test_capabilities(self):
        """Test codec capabilities"""
        caps = G722Codec.get_capabilities()
        
        self.assertIn('bitrates', caps)
        self.assertIn('sample_rate', caps)
        self.assertEqual(caps['sample_rate'], 16000)
        self.assertIn(64000, caps['bitrates'])
        self.assertIn(56000, caps['bitrates'])
        self.assertIn(48000, caps['bitrates'])
    
    def test_different_bitrates(self):
        """Test different bitrate modes"""
        codec_64k = G722Codec(bitrate=G722Codec.MODE_64K)
        codec_56k = G722Codec(bitrate=G722Codec.MODE_56K)
        codec_48k = G722Codec(bitrate=G722Codec.MODE_48K)
        
        self.assertEqual(codec_64k.bitrate, 64000)
        self.assertEqual(codec_56k.bitrate, 56000)
        self.assertEqual(codec_48k.bitrate, 48000)
    
    def test_encode_decode_roundtrip(self):
        """Test that encode/decode roundtrip preserves data shape"""
        codec = G722Codec()
        
        # Create test PCM data with some pattern (sine-like)
        import struct
        pcm_data = bytearray()
        for i in range(320):  # 320 samples = 640 bytes
            # Create a simple pattern
            value = int((i % 100) * 327 - 16384)
            pcm_data.extend(struct.pack('<h', value))
        pcm_data = bytes(pcm_data)
        
        # Encode
        encoded = codec.encode(pcm_data)
        self.assertIsNotNone(encoded)
        self.assertEqual(len(encoded), 160)  # 640 bytes / 4 = 160 bytes
        
        # Decode
        decoded = codec.decode(encoded)
        self.assertIsNotNone(decoded)
        self.assertEqual(len(decoded), 640)  # 160 bytes * 4 = 640 bytes (same as input)
        
        # Verify we can decode what we encoded (sizes should match pattern)
        # Note: Due to quantization, values won't be identical but shape should be preserved


class TestG722CodecManager(unittest.TestCase):
    """Test G.722 codec manager"""
    
    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = G722CodecManager()
        
        self.assertIsNotNone(manager)
        self.assertTrue(manager.enabled)
    
    def test_create_encoder(self):
        """Test encoder creation"""
        manager = G722CodecManager()
        
        encoder = manager.create_encoder('call-001')
        
        self.assertIsNotNone(encoder)
        self.assertIn('call-001', manager.encoders)
    
    def test_create_decoder(self):
        """Test decoder creation"""
        manager = G722CodecManager()
        
        decoder = manager.create_decoder('call-001')
        
        self.assertIsNotNone(decoder)
        self.assertIn('call-001', manager.decoders)
    
    def test_release_codec(self):
        """Test codec release"""
        manager = G722CodecManager()
        
        manager.create_encoder('call-001')
        manager.create_decoder('call-001')
        
        self.assertEqual(len(manager.encoders), 1)
        self.assertEqual(len(manager.decoders), 1)
        
        manager.release_codec('call-001')
        
        self.assertEqual(len(manager.encoders), 0)
        self.assertEqual(len(manager.decoders), 0)
    
    def test_get_statistics(self):
        """Test statistics retrieval"""
        manager = G722CodecManager()
        
        manager.create_encoder('call-001')
        manager.create_encoder('call-002')
        manager.create_decoder('call-001')
        
        stats = manager.get_statistics()
        
        self.assertEqual(stats['active_encoders'], 2)
        self.assertEqual(stats['active_decoders'], 1)
        self.assertTrue(stats['enabled'])
    
    def test_sdp_capabilities(self):
        """Test SDP capabilities"""
        manager = G722CodecManager()
        
        caps = manager.get_sdp_capabilities()
        
        self.assertIsInstance(caps, list)
        self.assertGreater(len(caps), 0)
    
    def test_disabled_manager(self):
        """Test manager when disabled"""
        config = {'codecs.g722.enabled': False}
        manager = G722CodecManager(config)
        
        self.assertFalse(manager.enabled)
        
        encoder = manager.create_encoder('call-001')
        self.assertIsNone(encoder)
    
    def test_custom_bitrate(self):
        """Test custom bitrate configuration"""
        config = {'codecs.g722.bitrate': G722Codec.MODE_48K}
        manager = G722CodecManager(config)
        
        self.assertEqual(manager.default_bitrate, 48000)


if __name__ == '__main__':
    unittest.main()
