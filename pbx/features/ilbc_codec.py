"""
iLBC Codec Support
Internet Low Bitrate Codec (iLBC) - RFC 3951, 3952

iLBC is a free, open speech codec designed for robust voice transmission
over packet-switched networks. It's particularly well-suited for VoIP
applications where packet loss is common.

Key Features:
- Royalty-free and patent-free
- Two modes: 20ms and 30ms frames
- Built-in packet loss concealment (PLC)
- Bitrates: 15.2 kbps (20ms) or 13.33 kbps (30ms)
- Sample rate: 8 kHz (narrowband)
"""

from typing import Any, Dict, Optional

from pbx.utils.logger import get_logger


class ILBCCodec:
    """
    iLBC codec handler for the PBX system

    iLBC (Internet Low Bitrate Codec) is designed for VoIP applications
    with packet loss. It provides good speech quality at low bitrates with
    robust packet loss concealment built into the codec itself.

    Frame Modes:
    - 20ms: 15.2 kbps, lower latency, more overhead
    - 30ms: 13.33 kbps, higher latency, less overhead (recommended)
    """

    # Codec parameters
    SAMPLE_RATE = 8000  # 8 kHz narrowband
    PAYLOAD_TYPE = 97  # Dynamic payload type (96-127)

    # Frame modes
    MODE_20MS = 20
    MODE_30MS = 30
    DEFAULT_MODE = MODE_30MS  # 30ms is recommended mode

    # Bitrates for each mode
    BITRATE_20MS = 15200  # 15.2 kbps
    BITRATE_30MS = 13330  # 13.33 kbps

    # Frame sizes (samples)
    FRAME_SIZE_20MS = 160  # 20ms at 8kHz
    FRAME_SIZE_30MS = 240  # 30ms at 8kHz

    # Encoded frame sizes (bytes)
    ENCODED_SIZE_20MS = 38  # bytes per 20ms frame
    ENCODED_SIZE_30MS = 50  # bytes per 30ms frame

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize iLBC codec handler

        Args:
            config: Optional configuration dictionary with:
                - mode: Frame duration (20 or 30 milliseconds, default: 30)
                - payload_type: RTP payload type (default: 97)
        """
        self.logger = get_logger()
        self.config = config or {}

        # Frame mode (20ms or 30ms)
        self.mode = self.config.get("mode", self.DEFAULT_MODE)
        if self.mode not in [self.MODE_20MS, self.MODE_30MS]:
            self.logger.warning(
                f"Invalid iLBC mode {self.mode}, using default {self.DEFAULT_MODE}ms"
            )
            self.mode = self.DEFAULT_MODE

        # Set parameters based on mode
        if self.mode == self.MODE_20MS:
            self.bitrate = self.BITRATE_20MS
            self.frame_size = self.FRAME_SIZE_20MS
            self.encoded_size = self.ENCODED_SIZE_20MS
        else:  # 30ms mode
            self.bitrate = self.BITRATE_30MS
            self.frame_size = self.FRAME_SIZE_30MS
            self.encoded_size = self.ENCODED_SIZE_30MS

        # Payload type
        self.payload_type = self.config.get("payload_type", self.PAYLOAD_TYPE)

        # Encoder/decoder state
        self.encoder = None
        self.decoder = None
        self.enabled = False

        # Check if ilbc library is available
        try:
            pass

            self.ilbc_available = True
            self.logger.info(
                f"iLBC codec initialized (mode: {self.mode}ms, "
                f"bitrate: {self.bitrate / 1000:.2f} kbps)"
            )
        except ImportError:
            self.ilbc_available = False
            self.logger.warning(
                "pyilbc library not available - iLBC codec will be "
                "negotiated but encoding/decoding will not work. "
                "Install with: pip install pyilbc"
            )

    def is_available(self) -> bool:
        """
        Check if iLBC codec is available

        Returns:
            bool: True if pyilbc library is available
        """
        return self.ilbc_available

    def get_info(self) -> Dict[str, Any]:
        """
        Get codec information

        Returns:
            Dict with codec details
        """
        return {
            "name": "iLBC",
            "full_name": "Internet Low Bitrate Codec",
            "sample_rate": self.SAMPLE_RATE,
            "mode": f"{self.mode}ms",
            "bitrate": self.bitrate,
            "frame_size": self.frame_size,
            "encoded_size": self.encoded_size,
            "payload_type": self.payload_type,
            "available": self.ilbc_available,
            "features": [
                "Packet loss concealment",
                "Low bitrate",
                "Royalty-free",
                "Narrowband (8 kHz)",
            ],
        }

    def get_sdp_description(self) -> str:
        """
        Get SDP description for iLBC codec

        Returns:
            str: SDP rtpmap attribute
        """
        # iLBC SDP format: rtpmap:<pt> iLBC/<sample_rate>
        # The mode is specified separately via fmtp
        return f"rtpmap:{self.payload_type} iLBC/{self.SAMPLE_RATE}"

    def get_fmtp(self) -> str:
        """
        Get SDP fmtp (format parameters) for iLBC

        Returns:
            str: SDP fmtp attribute specifying frame mode
        """
        return f"fmtp:{self.payload_type} mode={self.mode}"

    def get_sdp_parameters(self) -> Dict[str, Any]:
        """
        Get complete SDP parameters

        Returns:
            Dict with SDP negotiation parameters
        """
        return {
            "payload_type": self.payload_type,
            "encoding_name": "iLBC",
            "clock_rate": self.SAMPLE_RATE,
            "channels": 1,
            "mode": self.mode,
            "rtpmap": self.get_sdp_description(),
            "fmtp": self.get_fmtp(),
        }

    def create_encoder(self):
        """
        Create iLBC encoder

        This initializes the encoder state for encoding PCM to iLBC.
        """
        if not self.ilbc_available:
            self.logger.warning("Cannot create encoder - pyilbc not available")
            return

        try:
            import pyilbc

            self.encoder = pyilbc.Encoder(self.mode)
            self.logger.debug(f"iLBC encoder created (mode: {self.mode}ms)")
        except Exception as e:
            self.logger.error(f"Failed to create iLBC encoder: {e}")
            self.encoder = None

    def create_decoder(self):
        """
        Create iLBC decoder

        This initializes the decoder state for decoding iLBC to PCM.
        """
        if not self.ilbc_available:
            self.logger.warning("Cannot create decoder - pyilbc not available")
            return

        try:
            import pyilbc

            self.decoder = pyilbc.Decoder(self.mode)
            self.logger.debug(f"iLBC decoder created (mode: {self.mode}ms)")
        except Exception as e:
            self.logger.error(f"Failed to create iLBC decoder: {e}")
            self.decoder = None

    def encode(self, pcm_data: bytes) -> Optional[bytes]:
        """
        Encode PCM audio to iLBC

        Args:
            pcm_data: Raw PCM audio data (16-bit signed, mono, 8kHz)
                     Should be frame_size samples (160 or 240 samples)

        Returns:
            bytes: Encoded iLBC data, or None on error
        """
        if not self.encoder:
            self.logger.warning("Encoder not initialized - call create_encoder() first")
            return None

        # Verify input size
        expected_bytes = self.frame_size * 2  # 16-bit samples
        if len(pcm_data) != expected_bytes:
            self.logger.error(
                f"Invalid PCM data size: got {len(pcm_data)}, " f"expected {expected_bytes} bytes"
            )
            return None

        try:
            # Encode PCM to iLBC
            encoded = self.encoder.encode(pcm_data)
            return encoded
        except Exception as e:
            self.logger.error(f"iLBC encoding failed: {e}")
            return None

    def decode(self, ilbc_data: bytes) -> Optional[bytes]:
        """
        Decode iLBC audio to PCM

        Args:
            ilbc_data: Encoded iLBC data (38 or 50 bytes depending on mode)

        Returns:
            bytes: Decoded PCM audio (16-bit signed, mono, 8kHz), or None on error
        """
        if not self.decoder:
            self.logger.warning("Decoder not initialized - call create_decoder() first")
            return None

        # Verify input size
        if len(ilbc_data) != self.encoded_size:
            self.logger.error(
                f"Invalid iLBC data size: got {len(ilbc_data)}, "
                f"expected {self.encoded_size} bytes"
            )
            return None

        try:
            # Decode iLBC to PCM
            decoded = self.decoder.decode(ilbc_data)
            return decoded
        except Exception as e:
            self.logger.error(f"iLBC decoding failed: {e}")
            return None

    def handle_packet_loss(self) -> Optional[bytes]:
        """
        Generate concealment audio for lost packet

        iLBC has built-in packet loss concealment (PLC).
        Call this when a packet is lost to generate replacement audio.

        Returns:
            bytes: Concealment audio (same size as normal frame), or None on error
        """
        if not self.decoder:
            self.logger.warning("Decoder not initialized - call create_decoder() first")
            return None

        try:
            # Decode with None to trigger PLC
            concealed = self.decoder.decode(None)
            return concealed
        except Exception as e:
            self.logger.error(f"iLBC PLC failed: {e}")
            return None

    def reset_encoder(self):
        """Reset encoder state"""
        if self.encoder:
            self.create_encoder()  # Recreate encoder

    def reset_decoder(self):
        """Reset decoder state"""
        if self.decoder:
            self.create_decoder()  # Recreate decoder


class ILBCCodecManager:
    """
    Manager for iLBC codec instances

    Manages multiple iLBC codec instances for different calls.
    """

    def __init__(self, pbx):
        """
        Initialize iLBC codec manager

        Args:
            pbx: PBX instance
        """
        self.pbx = pbx
        self.logger = get_logger()
        self.codecs = {}  # call_id -> ILBCCodec

        # Get global config
        self.config = {}
        if hasattr(pbx, "config") and pbx.config:
            codec_config = pbx.config.get("codecs", {})
            self.config = codec_config.get("ilbc", {})

        self.logger.info("iLBC codec manager initialized")

    def create_codec(self, call_id: str, config: Optional[Dict[str, Any]] = None) -> ILBCCodec:
        """
        Create iLBC codec instance for a call

        Args:
            call_id: Unique call identifier
            config: Optional codec configuration (uses global config if not provided)

        Returns:
            ILBCCodec instance
        """
        # Use provided config or global config
        codec_config = config or self.config

        # Create codec instance
        codec = ILBCCodec(codec_config)
        self.codecs[call_id] = codec

        self.logger.debug(f"Created iLBC codec for call {call_id}")
        return codec

    def get_codec(self, call_id: str) -> Optional[ILBCCodec]:
        """
        Get codec instance for a call

        Args:
            call_id: Call identifier

        Returns:
            ILBCCodec instance or None
        """
        return self.codecs.get(call_id)

    def remove_codec(self, call_id: str):
        """
        Remove codec instance for a call

        Args:
            call_id: Call identifier
        """
        if call_id in self.codecs:
            del self.codecs[call_id]
            self.logger.debug(f"Removed iLBC codec for call {call_id}")

    def get_all_codecs(self) -> Dict[str, ILBCCodec]:
        """
        Get all codec instances

        Returns:
            Dict mapping call_id to ILBCCodec
        """
        return self.codecs.copy()

    def is_ilbc_available(self) -> bool:
        """
        Check if iLBC is available system-wide

        Returns:
            bool: True if pyilbc library is available
        """
        try:
            pass

            return True
        except ImportError:
            return False
