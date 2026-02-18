"""
G.729 Codec Support
ITU-T G.729 is a low-bitrate speech codec operating at 8 kbit/s.

This module provides G.729 codec integration with the PBX system.
When the bcg729 shared library is available on the system, encoding and
decoding are performed via ctypes bindings.  Otherwise, the codec reports
itself as unavailable and encode/decode return ``None``.

Supported native libraries (auto-detected via ctypes):
- libbcg729 (open-source, LGPL) -- Ubuntu: ``apt install libbcg729-0``
"""

import ctypes
import ctypes.util
from typing import Any

from pbx.utils.logger import get_logger

# ---------------------------------------------------------------------------
# bcg729 ctypes bindings
# ---------------------------------------------------------------------------
# bcg729 exposes a simple C API:
#   bcg729EncoderChannelContextStruct *initBcg729EncoderChannel(uint8_t enableVAD)
#   void closeBcg729EncoderChannel(bcg729EncoderChannelContextStruct *ctx)
#   void bcg729Encoder(bcg729EncoderChannelContextStruct *ctx,
#                      const int16_t *inputFrame, uint8_t *bitStream,
#                      uint8_t *bitStreamLength)
#
#   bcg729DecoderChannelContextStruct *initBcg729DecoderChannel()
#   void closeBcg729DecoderChannel(bcg729DecoderChannelContextStruct *ctx)
#   void bcg729Decoder(bcg729DecoderChannelContextStruct *ctx,
#                      const uint8_t *bitStream, uint8_t bitStreamLength,
#                      uint8_t isSID, uint8_t isLost, uint8_t isRinging,
#                      int16_t *outputFrame)
# ---------------------------------------------------------------------------

_bcg729_lib: Any | None = None
_BCG729_AVAILABLE: bool = False


def _load_bcg729() -> Any | None:
    """Attempt to load the bcg729 shared library via ctypes."""
    global _bcg729_lib, _BCG729_AVAILABLE

    if _bcg729_lib is not None:
        return _bcg729_lib

    lib_names = [
        "bcg729",
        "libbcg729",
        "libbcg729.so",
        "libbcg729.so.0",
        "libbcg729.dylib",
        "bcg729.dll",
    ]

    # Also try ctypes.util.find_library which searches standard paths
    found = ctypes.util.find_library("bcg729")
    if found:
        lib_names.insert(0, found)

    for name in lib_names:
        try:
            lib = ctypes.CDLL(name)

            # Verify the library has the functions we need
            lib.initBcg729EncoderChannel.restype = ctypes.c_void_p
            lib.initBcg729EncoderChannel.argtypes = [ctypes.c_uint8]

            lib.closeBcg729EncoderChannel.restype = None
            lib.closeBcg729EncoderChannel.argtypes = [ctypes.c_void_p]

            lib.bcg729Encoder.restype = None
            lib.bcg729Encoder.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_int16),
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.POINTER(ctypes.c_uint8),
            ]

            lib.initBcg729DecoderChannel.restype = ctypes.c_void_p
            lib.initBcg729DecoderChannel.argtypes = []

            lib.closeBcg729DecoderChannel.restype = None
            lib.closeBcg729DecoderChannel.argtypes = [ctypes.c_void_p]

            lib.bcg729Decoder.restype = None
            lib.bcg729Decoder.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_uint8,
                ctypes.c_uint8,
                ctypes.c_uint8,
                ctypes.c_uint8,
                ctypes.POINTER(ctypes.c_int16),
            ]

            _bcg729_lib = lib
            _BCG729_AVAILABLE = True
            return lib

        except OSError:
            continue

    return None


# Eagerly attempt to load on module import
_load_bcg729()


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
    SAMPLE_RATE = 8000  # 8 kHz narrowband
    FRAME_SIZE = 80  # 10ms frame at 8kHz (80 samples)
    FRAME_DURATION_MS = 10  # 10ms per frame
    PAYLOAD_TYPE = 18  # Standard RTP payload type for G.729
    BITRATE = 8000  # 8 kbit/s

    # G.729 encoded frame size: 10 bytes for a normal 10ms frame
    ENCODED_FRAME_SIZE = 10
    # SID (silence) frame size for Annex B
    SID_FRAME_SIZE = 2

    def __init__(self, variant: str = "G729AB") -> None:
        """
        Initialize G.729 codec

        Args:
            variant: G.729 variant ('G729', 'G729A', 'G729B', 'G729AB')
        """
        self.logger = get_logger()
        self.variant = variant

        # ctypes context pointers (managed per-instance)
        self._encoder_ctx: ctypes.c_void_p | None = None
        self._decoder_ctx: ctypes.c_void_p | None = None

        enable_vad = 1 if variant in ("G729B", "G729AB") else 0

        if _BCG729_AVAILABLE and _bcg729_lib is not None:
            self.enabled = True
            self._encoder_ctx = _bcg729_lib.initBcg729EncoderChannel(ctypes.c_uint8(enable_vad))
            self._decoder_ctx = _bcg729_lib.initBcg729DecoderChannel()

            if not self._encoder_ctx or not self._decoder_ctx:
                self.logger.error("bcg729: failed to create encoder/decoder context")
                self.enabled = False
            else:
                self.logger.debug(f"G.729 codec initialized with bcg729 (variant: {variant})")
        else:
            self.enabled = False
            self.logger.warning(
                "G.729 encoding/decoding requires the bcg729 library. "
                "Install libbcg729 (e.g. apt install libbcg729-0) for full support."
            )

    def encode(self, pcm_data: bytes) -> bytes | None:
        """
        Encode PCM audio to G.729

        Processes the input in 10 ms frames (80 samples = 160 bytes of 16-bit
        PCM).  Each frame produces 10 bytes of G.729 encoded data (or 2 bytes
        for a SID frame when VAD is active).

        Args:
            pcm_data: Raw PCM audio data (16-bit signed, 8 kHz, little-endian).
                      Length must be a multiple of 160 bytes (80 samples per
                      10 ms frame).

        Returns:
            Encoded G.729 data, or ``None`` if the codec is unavailable or
            encoding fails.
        """
        if not self.enabled or _bcg729_lib is None or self._encoder_ctx is None:
            self.logger.warning("G.729 encoding unavailable - bcg729 library not loaded")
            return None

        frame_bytes = self.FRAME_SIZE * 2  # 80 samples * 2 bytes per sample = 160
        if len(pcm_data) % frame_bytes != 0:
            self.logger.warning(
                f"PCM data length ({len(pcm_data)}) is not a multiple of "
                f"{frame_bytes} bytes (one G.729 frame)"
            )
            return None

        num_frames = len(pcm_data) // frame_bytes
        output = bytearray()

        for i in range(num_frames):
            offset = i * frame_bytes
            frame_pcm = pcm_data[offset : offset + frame_bytes]

            # Create ctypes arrays for the bcg729 call
            input_buf = (ctypes.c_int16 * self.FRAME_SIZE)()
            ctypes.memmove(input_buf, frame_pcm, frame_bytes)

            # Output buffer: max 10 bytes for a normal frame
            output_buf = (ctypes.c_uint8 * self.ENCODED_FRAME_SIZE)()
            output_len = ctypes.c_uint8(0)

            _bcg729_lib.bcg729Encoder(
                self._encoder_ctx,
                input_buf,
                output_buf,
                ctypes.byref(output_len),
            )

            encoded_len = output_len.value
            output.extend(bytes(output_buf)[:encoded_len])

        return bytes(output)

    def decode(self, g729_data: bytes) -> bytes | None:
        """
        Decode G.729 to PCM audio

        Accepts concatenated G.729 frames (10 bytes each for normal frames,
        2 bytes for SID frames).  Each decoded frame produces 80 samples
        (160 bytes) of 16-bit PCM.

        Args:
            g729_data: Encoded G.729 data (concatenated frames).

        Returns:
            Decoded PCM audio data (16-bit signed, 8 kHz, little-endian),
            or ``None`` if the codec is unavailable or decoding fails.
        """
        if not self.enabled or _bcg729_lib is None or self._decoder_ctx is None:
            self.logger.warning("G.729 decoding unavailable - bcg729 library not loaded")
            return None

        if len(g729_data) == 0:
            return b""

        output = bytearray()
        pos = 0
        data_len = len(g729_data)

        while pos < data_len:
            remaining = data_len - pos

            # Determine frame type by size
            if remaining >= self.ENCODED_FRAME_SIZE:
                frame_len = self.ENCODED_FRAME_SIZE
                is_sid = 0
            elif remaining >= self.SID_FRAME_SIZE:
                frame_len = self.SID_FRAME_SIZE
                is_sid = 1
            else:
                self.logger.warning(
                    f"Incomplete G.729 frame ({remaining} bytes remaining), skipping"
                )
                break

            frame_data = g729_data[pos : pos + frame_len]
            pos += frame_len

            input_buf = (ctypes.c_uint8 * frame_len)()
            ctypes.memmove(input_buf, frame_data, frame_len)

            output_buf = (ctypes.c_int16 * self.FRAME_SIZE)()

            _bcg729_lib.bcg729Decoder(
                self._decoder_ctx,
                input_buf,
                ctypes.c_uint8(frame_len),
                ctypes.c_uint8(is_sid),
                ctypes.c_uint8(0),  # isLost = False
                ctypes.c_uint8(0),  # isRinging = False
                output_buf,
            )

            # Convert output samples to bytes (16-bit LE)
            output.extend(bytes(output_buf))

        return bytes(output)

    def close(self) -> None:
        """Release bcg729 encoder/decoder contexts."""
        if _bcg729_lib is not None:
            if self._encoder_ctx is not None:
                _bcg729_lib.closeBcg729EncoderChannel(self._encoder_ctx)
                self._encoder_ctx = None
            if self._decoder_ctx is not None:
                _bcg729_lib.closeBcg729DecoderChannel(self._decoder_ctx)
                self._decoder_ctx = None

    def __del__(self) -> None:
        self.close()

    def get_info(self) -> dict:
        """
        Get codec information

        Returns:
            Dictionary with codec details
        """
        if _BCG729_AVAILABLE:
            impl = "bcg729 (native ctypes binding)"
        else:
            impl = "Unavailable (install libbcg729)"

        return {
            "name": "G.729",
            "variant": self.variant,
            "description": "Low-bitrate speech codec (8 kbit/s)",
            "sample_rate": self.SAMPLE_RATE,
            "bitrate": self.BITRATE,
            "frame_size": self.FRAME_SIZE,
            "frame_duration_ms": self.FRAME_DURATION_MS,
            "payload_type": self.PAYLOAD_TYPE,
            "enabled": self.enabled,
            "quality": "Good (Narrowband)",
            "bandwidth": "Low (8 kHz)",
            "implementation": impl,
            "license_required": False,
        }

    def get_sdp_description(self) -> str:
        """
        Get SDP format description for SIP negotiation

        Returns:
            SDP media format string
        """
        # G.729 uses 8000 Hz sample rate with one channel
        return f"rtpmap:{self.PAYLOAD_TYPE} G729/{self.SAMPLE_RATE}"

    def get_fmtp_params(self) -> str | None:
        """
        Get format parameters for SDP

        Returns:
            FMTP parameter string or None
        """
        # G.729 typically doesn't require fmtp parameters
        # Some implementations may use "fmtp:18 annexb=no" to disable Annex B
        if self.variant in ["G729", "G729A"]:
            # Disable Annex B (VAD/CNG) for base variants
            return f"fmtp:{self.PAYLOAD_TYPE} annexb=no"
        return None

    @staticmethod
    def is_supported() -> bool:
        """
        Check if G.729 codec library is available

        Returns:
            True if the bcg729 native library is available
        """
        # First check our ctypes-based detection (most reliable)
        if _BCG729_AVAILABLE:
            return True

        # Also check for Python wrapper packages
        for lib in ("bcg729", "g729"):
            try:
                __import__(lib)
                return True
            except ImportError:
                continue

        return False

    @staticmethod
    def get_capabilities() -> dict:
        """
        Get codec capabilities

        Returns:
            Dictionary with supported features
        """
        return {
            "variants": ["G729", "G729A", "G729B", "G729AB"],
            "sample_rate": 8000,
            "channels": 1,  # Mono
            "frame_sizes": [80],  # 10ms
            "bitrate": 8000,  # 8 kbit/s
            "complexity": "Medium",
            "latency": "Low (10-20ms)",
            "applications": ["VoIP", "Low-bandwidth scenarios"],
            "native_library": "bcg729" if _BCG729_AVAILABLE else "not available",
            "license_note": ("bcg729 is LGPL-licensed. G.729 patents have expired worldwide."),
        }


class G729CodecManager:
    """
    Manager for G.729 codec instances and configuration
    """

    def __init__(self, config: dict | None = None) -> None:
        """
        Initialize G.729 codec manager

        Args:
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get("codecs.g729.enabled", False)
        self.variant = self.config.get("codecs.g729.variant", "G729AB")

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

    def create_encoder(self, call_id: str, variant: str | None = None) -> G729Codec | None:
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

    def create_decoder(self, call_id: str, variant: str | None = None) -> G729Codec | None:
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

    def release_codec(self, call_id: str) -> None:
        """
        Release codec resources for a call

        Args:
            call_id: Call identifier
        """
        encoder = self.encoders.pop(call_id, None)
        if encoder is not None:
            encoder.close()

        decoder = self.decoders.pop(call_id, None)
        if decoder is not None:
            decoder.close()

        self.logger.debug(f"Released G.729 codecs for call {call_id}")

    def get_encoder(self, call_id: str) -> G729Codec | None:
        """Get encoder for a call"""
        return self.encoders.get(call_id)

    def get_decoder(self, call_id: str) -> G729Codec | None:
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
            "variant": self.variant,
            "active_encoders": len(self.encoders),
            "active_decoders": len(self.decoders),
            "supported": G729Codec.is_supported(),
        }

    def get_sdp_capabilities(self) -> list:
        """
        Get SDP capabilities for SIP negotiation

        Returns:
            list of SDP format lines
        """
        if not self.enabled:
            return []

        codec = G729Codec(self.variant)
        capabilities = [f"a={codec.get_sdp_description()}"]

        fmtp = codec.get_fmtp_params()
        if fmtp:
            capabilities.append(f"a={fmtp}")

        return capabilities
