"""
G.729 Codec Support
ITU-T G.729 is a low-bitrate speech codec operating at 8 kbit/s.

This module provides framework support for G.729 codec negotiation and
integration with the PBX system. The actual encoding/decoding typically
requires a licensed library (e.g., Intel IPP, Broadcom, or open-source implementations).

For production use, integrate with a G.729 codec library.
"""
from typing import Optional

from pbx.utils.logger import get_logger


class G729Codec:
    """
    G.729 codec framework implementation
    
    G.729 is a narrowband speech codec standardized by ITU-T that compresses
    64 kbit/s G.711 signals into 8 kbit/s streams. It's widely used in VoIP
    due to its excellent compression and quality.
    
    Variants:
    - G.729: Original version (8 kbit/s)
    - G.729A: Simplified version with slightly lower quality
    - G.729B: Adds Voice Activity Detection (VAD) and Comfort Noise Generation (CNG)
    - G.729AB: Most common variant combining A and B features
    """
    
    # Codec parameters
    SAMPLE_RATE = 8000       # 8 kHz narrowband
    FRAME_SIZE = 80          # 10ms frame at 8kHz (80 samples)
    FRAME_DURATION_MS = 10   # 10ms per frame
    PAYLOAD_TYPE = 18        # Standard RTP payload type for G.729
    BITRATE = 8000          # 8 kbit/s
    
    def __init__(self, variant: str = 'G729AB'):
        """
        Initialize G.729 codec
        
        Args:
            variant: G.729 variant ('G729', 'G729A', 'G729B', 'G729AB')
        """
        self.logger = get_logger()
        self.variant = variant
        self.enabled = False  # Disabled by default (requires codec library)
        
        self.logger.debug(f"G.729 codec initialized (variant: {variant})")
        self.logger.warning(
            "G.729 encoding/decoding requires a licensed codec library. "
            "Currently providing framework support for codec negotiation only."
        )
    
    def encode(self, pcm_data: bytes) -> Optional[bytes]:
        """
        Encode PCM audio to G.729
        
        Args:
            pcm_data: Raw PCM audio data (16-bit signed, 8kHz, little-endian)
        
        Returns:
            Encoded G.729 data or None (not implemented)
            
        Note:
            This is a stub implementation. For production use, integrate with
            a G.729 codec library such as:
            - Intel IPP codec
            - Broadcom/Sipro G.729
            - bcg729 (open-source implementation)
        """
        self.logger.warning("G.729 encoding not implemented - requires codec library")
        return None
    
    def decode(self, g729_data: bytes) -> Optional[bytes]:
        """
        Decode G.729 to PCM audio
        
        Args:
            g729_data: Encoded G.729 data
        
        Returns:
            Decoded PCM audio data or None (not implemented)
            
        Note:
            This is a stub implementation. For production use, integrate with
            a G.729 codec library.
        """
        self.logger.warning("G.729 decoding not implemented - requires codec library")
        return None
    
    def get_info(self) -> dict:
        """
        Get codec information
        
        Returns:
            Dictionary with codec details
        """
        return {
            'name': 'G.729',
            'variant': self.variant,
            'description': 'Low-bitrate speech codec (8 kbit/s)',
            'sample_rate': self.SAMPLE_RATE,
            'bitrate': self.BITRATE,
            'frame_size': self.FRAME_SIZE,
            'frame_duration_ms': self.FRAME_DURATION_MS,
            'payload_type': self.PAYLOAD_TYPE,
            'enabled': self.enabled,
            'quality': 'Good (Narrowband)',
            'bandwidth': 'Low (8 kHz)',
            'implementation': 'Framework Only (requires codec library)',
            'license_required': True
        }
    
    def get_sdp_description(self) -> str:
        """
        Get SDP format description for SIP negotiation
        
        Returns:
            SDP media format string
        """
        # G.729 uses 8000 Hz sample rate with one channel
        return f"rtpmap:{self.PAYLOAD_TYPE} G729/{self.SAMPLE_RATE}"
    
    def get_fmtp_params(self) -> Optional[str]:
        """
        Get format parameters for SDP
        
        Returns:
            FMTP parameter string or None
        """
        # G.729 typically doesn't require fmtp parameters
        # Some implementations may use "fmtp:18 annexb=no" to disable Annex B
        if self.variant in ['G729', 'G729A']:
            # Disable Annex B (VAD/CNG) for base variants
            return f"fmtp:{self.PAYLOAD_TYPE} annexb=no"
        return None
    
    @staticmethod
    def is_supported() -> bool:
        """
        Check if G.729 codec library is available
        
        Returns:
            True if codec library is available
        """
        # Check for codec library availability
        # Try to import G.729 library (examples)
        try:
            # Example: import bcg729
            # return True
            pass
        except ImportError:
            pass
        
        return False
    
    @staticmethod
    def get_capabilities() -> dict:
        """
        Get codec capabilities
        
        Returns:
            Dictionary with supported features
        """
        return {
            'variants': ['G729', 'G729A', 'G729B', 'G729AB'],
            'sample_rate': 8000,
            'channels': 1,  # Mono
            'frame_sizes': [80],  # 10ms
            'bitrate': 8000,  # 8 kbit/s
            'complexity': 'Medium',
            'latency': 'Low (10-20ms)',
            'applications': ['VoIP', 'Low-bandwidth scenarios'],
            'license_note': 'May require patent license depending on jurisdiction'
        }


class G729CodecManager:
    """
    Manager for G.729 codec instances and configuration
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize G.729 codec manager
        
        Args:
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get('codecs.g729.enabled', False)
        self.variant = self.config.get('codecs.g729.variant', 'G729AB')
        
        # Codec instances cache
        self.encoders = {}  # call_id -> encoder instance
        self.decoders = {}  # call_id -> decoder instance
        
        if self.enabled:
            if not G729Codec.is_supported():
                self.logger.warning(
                    "G.729 codec enabled in config but codec library not available. "
                    "Codec negotiation will be supported but encoding/decoding will not work."
                )
            self.logger.info(f"G.729 codec manager initialized (variant: {self.variant})")
        else:
            self.logger.info("G.729 codec disabled in configuration")
    
    def create_encoder(self, call_id: str, variant: str = None) -> Optional[G729Codec]:
        """
        Create encoder for a call
        
        Args:
            call_id: Call identifier
            variant: Optional codec variant (defaults to config)
        
        Returns:
            G729Codec instance or None
        """
        if not self.enabled:
            return None
        
        variant = variant or self.variant
        encoder = G729Codec(variant=variant)
        self.encoders[call_id] = encoder
        
        self.logger.debug(f"Created G.729 encoder for call {call_id}")
        return encoder
    
    def create_decoder(self, call_id: str, variant: str = None) -> Optional[G729Codec]:
        """
        Create decoder for a call
        
        Args:
            call_id: Call identifier
            variant: Optional codec variant (defaults to config)
        
        Returns:
            G729Codec instance or None
        """
        if not self.enabled:
            return None
        
        variant = variant or self.variant
        decoder = G729Codec(variant=variant)
        self.decoders[call_id] = decoder
        
        self.logger.debug(f"Created G.729 decoder for call {call_id}")
        return decoder
    
    def release_codec(self, call_id: str):
        """
        Release codec resources for a call
        
        Args:
            call_id: Call identifier
        """
        if call_id in self.encoders:
            del self.encoders[call_id]
        
        if call_id in self.decoders:
            del self.decoders[call_id]
        
        self.logger.debug(f"Released G.729 codecs for call {call_id}")
    
    def get_encoder(self, call_id: str) -> Optional[G729Codec]:
        """Get encoder for a call"""
        return self.encoders.get(call_id)
    
    def get_decoder(self, call_id: str) -> Optional[G729Codec]:
        """Get decoder for a call"""
        return self.decoders.get(call_id)
    
    def get_statistics(self) -> dict:
        """
        Get codec usage statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'enabled': self.enabled,
            'variant': self.variant,
            'active_encoders': len(self.encoders),
            'active_decoders': len(self.decoders),
            'supported': G729Codec.is_supported()
        }
    
    def get_sdp_capabilities(self) -> list:
        """
        Get SDP capabilities for SIP negotiation
        
        Returns:
            List of SDP format lines
        """
        if not self.enabled:
            return []
        
        codec = G729Codec(self.variant)
        capabilities = [f"a={codec.get_sdp_description()}"]
        
        fmtp = codec.get_fmtp_params()
        if fmtp:
            capabilities.append(f"a={fmtp}")
        
        return capabilities
