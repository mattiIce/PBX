"""
Video Codec Support (H.264/H.265)
Framework for video codecs using free libraries (x264/x265)
"""
from typing import Dict, Optional, Tuple
from pbx.utils.logger import get_logger

# Try to import video codec libraries (all free/opensource)
try:
    import av  # PyAV - free FFmpeg bindings
    PYAV_AVAILABLE = True
except ImportError:
    PYAV_AVAILABLE = False


class VideoCodecManager:
    """Manager for video codecs (H.264, H.265, VP8, VP9)"""
    
    # Supported codecs (all free)
    SUPPORTED_CODECS = {
        'h264': {'name': 'H.264/AVC', 'library': 'x264', 'max_resolution': '4K'},
        'h265': {'name': 'H.265/HEVC', 'library': 'x265', 'max_resolution': '8K'},
        'vp8': {'name': 'VP8', 'library': 'libvpx', 'max_resolution': '4K'},
        'vp9': {'name': 'VP9', 'library': 'libvpx', 'max_resolution': '8K'},
    }
    
    def __init__(self, config=None):
        """Initialize video codec manager"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get('features', {}).get('video_codecs', {}).get('enabled', False)
        self.preferred_codec = self.config.get('features', {}).get('video_codecs', {}).get('preferred', 'h264')
        
        if self.enabled and not PYAV_AVAILABLE:
            self.logger.warning("Video codecs enabled but PyAV not installed. Install with: pip install av")
        elif self.enabled:
            self.logger.info(f"Video codec manager initialized (PyAV available)")
            self.logger.info(f"  Preferred codec: {self.preferred_codec}")
    
    def get_supported_codecs(self) -> Dict:
        """Get list of supported video codecs"""
        return self.SUPPORTED_CODECS
    
    def is_codec_supported(self, codec_name: str) -> bool:
        """Check if a codec is supported"""
        return codec_name.lower() in self.SUPPORTED_CODECS
    
    def get_codec_info(self, codec_name: str) -> Optional[Dict]:
        """Get information about a specific codec"""
        return self.SUPPORTED_CODECS.get(codec_name.lower())
    
    def encode_frame(self, frame_data: bytes, codec: str = 'h264', 
                     width: int = 1920, height: int = 1080,
                     bitrate: int = 2000000) -> Optional[bytes]:
        """
        Encode a video frame
        
        Args:
            frame_data: Raw frame data
            codec: Codec to use (h264, h265, vp8, vp9)
            width: Frame width
            height: Frame height
            bitrate: Target bitrate in bps
            
        Returns:
            Encoded frame data or None on error
        """
        if not self.enabled or not PYAV_AVAILABLE:
            return None
        
        try:
            # Stub implementation - would use PyAV for actual encoding
            self.logger.debug(f"Encoding frame with {codec} ({width}x{height})")
            # In production, this would use av.VideoFrame and av.CodecContext
            return frame_data  # Placeholder
        except Exception as e:
            self.logger.error(f"Error encoding frame: {e}")
            return None
    
    def decode_frame(self, encoded_data: bytes, codec: str = 'h264') -> Optional[bytes]:
        """
        Decode a video frame
        
        Args:
            encoded_data: Encoded frame data
            codec: Codec used for encoding
            
        Returns:
            Raw frame data or None on error
        """
        if not self.enabled or not PYAV_AVAILABLE:
            return None
        
        try:
            # Stub implementation - would use PyAV for actual decoding
            self.logger.debug(f"Decoding frame with {codec}")
            # In production, this would use av.CodecContext
            return encoded_data  # Placeholder
        except Exception as e:
            self.logger.error(f"Error decoding frame: {e}")
            return None
    
    def get_resolution_preset(self, preset: str) -> Tuple[int, int]:
        """
        Get resolution dimensions for a preset
        
        Args:
            preset: Resolution preset name
            
        Returns:
            Tuple of (width, height)
        """
        presets = {
            '480p': (854, 480),
            '720p': (1280, 720),
            '1080p': (1920, 1080),
            '1440p': (2560, 1440),
            '4k': (3840, 2160),
            '8k': (7680, 4320)
        }
        return presets.get(preset.lower(), (1920, 1080))
    
    def get_recommended_bitrate(self, width: int, height: int, fps: int = 30) -> int:
        """
        Calculate recommended bitrate for given resolution
        
        Args:
            width: Frame width
            height: Frame height
            fps: Frames per second
            
        Returns:
            Recommended bitrate in bps
        """
        # Simple calculation: pixels * fps * bits_per_pixel
        pixels = width * height
        bits_per_pixel = 0.1  # Conservative estimate
        bitrate = int(pixels * fps * bits_per_pixel)
        
        # Clamp to reasonable values
        min_bitrate = 500000  # 500 kbps
        max_bitrate = 50000000  # 50 Mbps
        return max(min_bitrate, min(bitrate, max_bitrate))
    
    def get_statistics(self) -> Dict:
        """Get video codec statistics"""
        return {
            'enabled': self.enabled,
            'pyav_available': PYAV_AVAILABLE,
            'preferred_codec': self.preferred_codec,
            'supported_codecs': list(self.SUPPORTED_CODECS.keys())
        }
