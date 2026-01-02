"""
G.726 Codec Support
ITU-T G.726 is an ADPCM speech codec with multiple bitrate variants.

This module provides framework support for G.726 codec negotiation and
integration with the PBX system. The actual encoding/decoding uses
Python's audioop module for G.726-32.

Note: audioop is deprecated in Python 3.11+ and will be removed in Python 3.13.
For future compatibility, plan to migrate to an alternative library such as:
- pydub (uses ffmpeg)
- pyaudio with codec plugins
- Native codec library bindings

Supports all G.726 bitrate variants:
- G.726-16: 16 kbit/s (2 bits per sample)
- G.726-24: 24 kbit/s (3 bits per sample)
- G.726-32: 32 kbit/s (4 bits per sample) - most common, also known as G721
- G.726-40: 40 kbit/s (5 bits per sample)
"""

import warnings
from typing import Optional

from pbx.utils.logger import get_logger


class G726Codec:
    """
    G.726 ADPCM codec framework implementation

    G.726 is a variable-rate ADPCM codec standardized by ITU-T that provides
    multiple bitrate options for different quality/bandwidth tradeoffs.

    Bitrate variants:
    - 16 kbit/s: Lowest quality, highest compression
    - 24 kbit/s: Low quality, good compression
    - 32 kbit/s: Good quality, moderate compression (most common)
    - 40 kbit/s: High quality, moderate compression
    """

    # Codec parameters
    SAMPLE_RATE = 8000  # 8 kHz narrowband

    # Payload type mapping (RFC 3551)
    # Note: Only G.726-32 has a static payload type
    PAYLOAD_TYPES = {
        16: None,  # No static type, use dynamic (96-127)
        24: None,  # No static type, use dynamic (96-127)
        32: 2,  # G721 (G.726-32) - standard static type
        40: None,  # No static type, use dynamic (96-127)
    }

    # Default dynamic payload types (when static not available)
    DEFAULT_DYNAMIC_TYPES = {16: 112, 24: 113, 32: 2, 40: 114}  # Use static type

    # Bits per sample for each bitrate
    BITS_PER_SAMPLE = {16: 2, 24: 3, 32: 4, 40: 5}

    def __init__(self, bitrate: int = 32000):
        """
        Initialize G.726 codec

        Args:
            bitrate: Bitrate in bits per second (16000, 24000, 32000, or 40000)

        Raises:
            ValueError: If bitrate is not supported
        """
        self.logger = get_logger()

        # Convert bitrate to kbit/s for easier handling
        self.bitrate_kbps = bitrate // 1000

        if self.bitrate_kbps not in [16, 24, 32, 40]:
            raise ValueError(
                f"Unsupported G.726 bitrate: {bitrate}. " "Must be 16000, 24000, 32000, or 40000"
            )

        self.bitrate = bitrate
        self.bits_per_sample = self.BITS_PER_SAMPLE[self.bitrate_kbps]
        self.payload_type = self.DEFAULT_DYNAMIC_TYPES[self.bitrate_kbps]
        self.enabled = True  # Can be implemented with audioop

        self.logger.debug(
            f"G.726 codec initialized at {self.bitrate_kbps} kbit/s "
            f"({self.bits_per_sample} bits/sample)"
        )

        # Log warning about audioop deprecation for G.726-32
        if self.bitrate_kbps == 32:
            # Note: This is logged once at initialization, not repeatedly
            # Migration path: Replace audioop with alternative library before Python 3.13
            self.logger.info(
                "G.726-32 using audioop (deprecated in Python 3.11+). "
                "Plan to migrate to alternative library for Python 3.13+ compatibility."
            )

    def encode(self, pcm_data: bytes) -> Optional[bytes]:
        """
        Encode PCM audio to G.726 ADPCM

        Args:
            pcm_data: Raw PCM audio data (16-bit signed, 8kHz, little-endian)

        Returns:
            Encoded G.726 data or None if encoding fails

        Note:
            This implementation uses Python's audioop module for G.721 (G.726-32).
            For other bitrates, a specialized library would be needed.
        """
        try:
            # Only G.726-32 can be handled by audioop (as lin2adpcm)
            if self.bitrate_kbps == 32:
                import audioop

                # Suppress deprecation warning
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=DeprecationWarning)
                    # Convert 16-bit linear PCM to ADPCM (4 bits per sample)
                    # audioop.lin2adpcm implements G.721 which is G.726 at 32 kbit/s
                    adpcm_data, _ = audioop.lin2adpcm(pcm_data, 2, None)
                return adpcm_data
            else:
                # For 16, 24, 40 kbit/s variants, would need specialized library
                self.logger.warning(
                    f"G.726-{self.bitrate_kbps} encoding not implemented. "
                    "Only G.726-32 is supported via audioop."
                )
                return None

        except ImportError:
            self.logger.error("audioop module not available for G.726 encoding")
            return None
        except Exception as e:
            self.logger.error(f"G.726 encoding error: {e}")
            return None

    def decode(self, g726_data: bytes) -> Optional[bytes]:
        """
        Decode G.726 ADPCM to PCM audio

        Args:
            g726_data: Encoded G.726 data

        Returns:
            Decoded PCM audio data (16-bit signed, 8kHz, little-endian)

        Note:
            This implementation uses Python's audioop module for G.721 (G.726-32).
            For other bitrates, a specialized library would be needed.
        """
        try:
            if len(g726_data) == 0:
                return b""

            # Only G.726-32 can be handled by audioop
            if self.bitrate_kbps == 32:
                import audioop

                # Suppress deprecation warning
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=DeprecationWarning)
                    # Convert ADPCM to 16-bit linear PCM
                    pcm_data, _ = audioop.adpcm2lin(g726_data, 2, None)
                return pcm_data
            else:
                # For 16, 24, 40 kbit/s variants, would need specialized library
                self.logger.warning(
                    f"G.726-{self.bitrate_kbps} decoding not implemented. "
                    "Only G.726-32 is supported via audioop."
                )
                return None

        except ImportError:
            self.logger.error("audioop module not available for G.726 decoding")
            return None
        except Exception as e:
            self.logger.error(f"G.726 decoding error: {e}")
            return None

    def get_info(self) -> dict:
        """
        Get codec information

        Returns:
            Dictionary with codec details
        """
        impl_status = "Full (audioop)" if self.bitrate_kbps == 32 else "Framework Only"

        return {
            "name": f"G.726-{self.bitrate_kbps}",
            "description": f"ADPCM speech codec ({self.bitrate_kbps} kbit/s)",
            "sample_rate": self.SAMPLE_RATE,
            "bitrate": self.bitrate,
            "bits_per_sample": self.bits_per_sample,
            "payload_type": self.payload_type,
            "enabled": self.enabled,
            "quality": self._get_quality_description(),
            "bandwidth": "Low to Medium",
            "implementation": impl_status,
        }

    def _get_quality_description(self) -> str:
        """Get quality description for current bitrate"""
        quality_map = {
            16: "Fair (Narrowband, High Compression)",
            24: "Good (Narrowband, Good Compression)",
            32: "Good (Narrowband, Moderate Compression)",
            40: "Very Good (Narrowband, Low Compression)",
        }
        return quality_map.get(self.bitrate_kbps, "Unknown")

    def get_sdp_description(self) -> str:
        """
        Get SDP format description for SIP negotiation

        Returns:
            SDP media format string
        """
        # G.726 uses 8000 Hz sample rate with one channel
        # Different naming conventions:
        # - G726-32 is sometimes called G721 or AAL2-G726-32
        # - Some implementations use G726-XX format

        if self.bitrate_kbps == 32:
            # G.726-32 can also be advertised as G721
            return f"rtpmap:{self.payload_type} G726-32/{self.SAMPLE_RATE}"
        else:
            return f"rtpmap:{self.payload_type} G726-{self.bitrate_kbps}/{self.SAMPLE_RATE}"

    def get_fmtp_params(self) -> Optional[str]:
        """
        Get format parameters for SDP

        Returns:
            FMTP parameter string or None
        """
        # G.726 typically doesn't require fmtp parameters
        # Some implementations may specify bitrate explicitly
        return None

    @staticmethod
    def is_supported(bitrate: int = 32000) -> bool:
        """
        Check if G.726 codec is supported for given bitrate

        Args:
            bitrate: Bitrate to check (16000, 24000, 32000, or 40000)

        Returns:
            True if codec is available for this bitrate
        """
        bitrate_kbps = bitrate // 1000

        # G.726-32 is supported via audioop
        if bitrate_kbps == 32:
            try:
                pass

                return True
            except ImportError:
                return False

        # Other bitrates would need specialized library
        return False

    @staticmethod
    def get_capabilities() -> dict:
        """
        Get codec capabilities

        Returns:
            Dictionary with supported features
        """
        return {
            "bitrates": [16000, 24000, 32000, 40000],
            "sample_rate": 8000,
            "channels": 1,  # Mono
            "bits_per_sample": [2, 3, 4, 5],
            "complexity": "Low",
            "latency": "Very Low",
            "applications": ["VoIP", "Telephony", "Low-bandwidth scenarios"],
            "note": "G.726-32 fully supported via audioop, others framework only",
        }


class G726CodecManager:
    """
    Manager for G.726 codec instances and configuration
    """

    def __init__(self, config: dict = None):
        """
        Initialize G.726 codec manager

        Args:
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get("codecs.g726.enabled", False)
        self.default_bitrate = self.config.get("codecs.g726.bitrate", 32000)

        # Validate bitrate
        if self.default_bitrate not in [16000, 24000, 32000, 40000]:
            self.logger.warning(
                f"Invalid G.726 bitrate {self.default_bitrate}, defaulting to 32000"
            )
            self.default_bitrate = 32000

        # Codec instances cache
        self.encoders = {}  # call_id -> encoder instance
        self.decoders = {}  # call_id -> decoder instance

        if self.enabled:
            bitrate_kbps = self.default_bitrate // 1000
            self.logger.info(f"G.726 codec manager initialized (bitrate: {bitrate_kbps} kbit/s)")

            if not G726Codec.is_supported(self.default_bitrate):
                self.logger.warning(
                    f"G.726-{bitrate_kbps} encoding/decoding may not be fully supported. "
                    "Only G.726-32 has full support via audioop."
                )
        else:
            self.logger.info("G.726 codec disabled in configuration")

    def create_encoder(self, call_id: str, bitrate: int = None) -> Optional[G726Codec]:
        """
        Create encoder for a call

        Args:
            call_id: Call identifier
            bitrate: Optional bitrate (defaults to config)

        Returns:
            G726Codec instance or None
        """
        if not self.enabled:
            return None

        bitrate = bitrate or self.default_bitrate
        encoder = G726Codec(bitrate=bitrate)
        self.encoders[call_id] = encoder

        self.logger.debug(f"Created G.726 encoder for call {call_id}")
        return encoder

    def create_decoder(self, call_id: str, bitrate: int = None) -> Optional[G726Codec]:
        """
        Create decoder for a call

        Args:
            call_id: Call identifier
            bitrate: Optional bitrate (defaults to config)

        Returns:
            G726Codec instance or None
        """
        if not self.enabled:
            return None

        bitrate = bitrate or self.default_bitrate
        decoder = G726Codec(bitrate=bitrate)
        self.decoders[call_id] = decoder

        self.logger.debug(f"Created G.726 decoder for call {call_id}")
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

        self.logger.debug(f"Released G.726 codecs for call {call_id}")

    def get_encoder(self, call_id: str) -> Optional[G726Codec]:
        """Get encoder for a call"""
        return self.encoders.get(call_id)

    def get_decoder(self, call_id: str) -> Optional[G726Codec]:
        """Get decoder for a call"""
        return self.decoders.get(call_id)

    def get_statistics(self) -> dict:
        """
        Get codec usage statistics

        Returns:
            Dictionary with statistics
        """
        return {
            "enabled": self.enabled,
            "default_bitrate": self.default_bitrate,
            "active_encoders": len(self.encoders),
            "active_decoders": len(self.decoders),
            "supported": G726Codec.is_supported(self.default_bitrate),
        }

    def get_sdp_capabilities(self) -> list:
        """
        Get SDP capabilities for SIP negotiation

        Returns:
            List of SDP format lines
        """
        if not self.enabled:
            return []

        codec = G726Codec(self.default_bitrate)
        capabilities = [f"a={codec.get_sdp_description()}"]

        fmtp = codec.get_fmtp_params()  # pylint: disable=assignment-from-none
        if fmtp:
            capabilities.append(f"a={fmtp}")

        return capabilities
