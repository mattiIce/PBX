"""
Speex Codec Support
Speex is a free, open-source speech codec designed for VoIP applications.

Speex is developed by Xiph.Org Foundation and is optimized for speech
compression. It supports multiple bandwidths (narrowband, wideband, ultra-wideband)
and variable bitrate operation.

Key Features:
- BSD License (royalty-free)
- Multiple bandwidth modes (8kHz, 16kHz, 32kHz)
- Variable bitrate (VBR) and adaptive bitrate
- Voice Activity Detection (VAD)
- Discontinuous Transmission (DTX)
- Acoustic echo cancellation
- Noise suppression

Note: Speex is being gradually superseded by Opus for new applications,
but it remains widely deployed and supported.
"""

from typing import Any, ClassVar

from pbx.utils.logger import get_logger


class SpeexCodec:
    """
    Speex codec handler for the PBX system

    Speex is optimized for speech and supports three bandwidth modes:
    - Narrowband: 8 kHz (telephone quality)
    - Wideband: 16 kHz (better quality)
    - Ultra-wideband: 32 kHz (highest quality)

    Each mode supports variable bitrate encoding for optimal quality/bandwidth
    tradeoff based on network conditions.
    """

    # Bandwidth modes
    MODE_NARROWBAND = "nb"  # 8 kHz
    MODE_WIDEBAND = "wb"  # 16 kHz
    MODE_ULTRA_WIDEBAND = "uwb"  # 32 kHz
    DEFAULT_MODE = MODE_NARROWBAND

    # Sample rates for each mode
    SAMPLE_RATES: ClassVar[dict[str, int]] = {MODE_NARROWBAND: 8000, MODE_WIDEBAND: 16000, MODE_ULTRA_WIDEBAND: 32000}

    # Payload types (RFC 5574)
    # Ensure no conflicts with iLBC (PT 97)
    PAYLOAD_TYPES: ClassVar[dict[str, int]] = {
        MODE_NARROWBAND: 98,  # PT 98 for narrowband (8kHz)
        MODE_WIDEBAND: 99,  # PT 99 for wideband (16kHz)
        MODE_ULTRA_WIDEBAND: 100,  # PT 100 for ultra-wideband (32kHz)
    }

    # Typical bitrates (VBR can vary)
    BITRATES: ClassVar[dict[str, dict[str, int]]] = {
        MODE_NARROWBAND: {
            "min": 2150,  # 2.15 kbps
            "typical": 8000,  # 8 kbps
            "max": 24600,  # 24.6 kbps
        },
        MODE_WIDEBAND: {
            "min": 3950,  # 3.95 kbps
            "typical": 16000,  # 16 kbps
            "max": 42200,  # 42.2 kbps
        },
        MODE_ULTRA_WIDEBAND: {
            "min": 4150,  # 4.15 kbps
            "typical": 28000,  # 28 kbps
            "max": 44000,  # 44 kbps
        },
    }

    # Frame sizes (20ms is standard)
    FRAME_DURATION_MS = 20

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize Speex codec handler

        Args:
            config: Optional configuration dictionary with:
                - mode: Bandwidth mode ('nb', 'wb', 'uwb', default: 'nb')
                - quality: Quality level 0-10 (default: 8)
                - complexity: Complexity level 1-10 (default: 3)
                - vbr: Enable Variable Bitrate (default: True)
                - vad: Enable Voice Activity Detection (default: True)
                - dtx: Enable Discontinuous Transmission (default: False)
                - payload_type: RTP payload type (default: based on mode)
        """
        self.logger = get_logger()
        self.config = config or {}

        # Bandwidth mode
        self.mode = self.config.get("mode", self.DEFAULT_MODE)
        if self.mode not in self.SAMPLE_RATES:
            self.logger.warning(f"Invalid Speex mode {self.mode}, using {self.DEFAULT_MODE}")
            self.mode = self.DEFAULT_MODE

        # Codec parameters
        self.sample_rate = self.SAMPLE_RATES[self.mode]
        self.quality = self.config.get("quality", 8)  # 0-10, 8 is good
        self.complexity = self.config.get("complexity", 3)  # 1-10

        # Features
        self.vbr_enabled = self.config.get("vbr", True)  # Variable Bitrate
        self.vad_enabled = self.config.get("vad", True)  # Voice Activity Detection
        self.dtx_enabled = self.config.get("dtx", False)  # Discontinuous Transmission

        # Payload type
        self.payload_type = self.config.get("payload_type", self.PAYLOAD_TYPES[self.mode])

        # Frame parameters
        self.frame_duration_ms = self.FRAME_DURATION_MS
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)

        # Bitrate info
        bitrate_info = self.BITRATES[self.mode]
        self.min_bitrate = bitrate_info["min"]
        self.typical_bitrate = bitrate_info["typical"]
        self.max_bitrate = bitrate_info["max"]

        # Encoder/decoder state
        self.encoder = None
        self.decoder = None
        self.enabled = False

        # Check if speex library is available
        try:
            self.speex_available = True
            self.logger.info(
                f"Speex codec initialized (mode: {self.mode}, "
                f"sample_rate: {self.sample_rate} Hz, quality: {self.quality})"
            )
        except ImportError:
            self.speex_available = False
            self.logger.warning(
                "speex library not available - Speex codec will be "
                "negotiated but encoding/decoding will not work. "
                "Install with: pip install speex"
            )

    def is_available(self) -> bool:
        """
        Check if Speex codec is available

        Returns:
            bool: True if speex library is available
        """
        return self.speex_available

    def get_info(self) -> dict[str, Any]:
        """
        Get codec information

        Returns:
            dict with codec details
        """
        mode_names = {
            self.MODE_NARROWBAND: "Narrowband",
            self.MODE_WIDEBAND: "Wideband",
            self.MODE_ULTRA_WIDEBAND: "Ultra-wideband",
        }

        features = ["Royalty-free", "BSD License"]
        if self.vbr_enabled:
            features.append("Variable Bitrate")
        if self.vad_enabled:
            features.append("Voice Activity Detection")
        if self.dtx_enabled:
            features.append("Discontinuous Transmission")

        return {
            "name": "Speex",
            "full_name": "Speex Speech Codec",
            "mode": mode_names[self.mode],
            "sample_rate": self.sample_rate,
            "quality": self.quality,
            "complexity": self.complexity,
            "frame_duration_ms": self.frame_duration_ms,
            "frame_size": self.frame_size,
            "min_bitrate": self.min_bitrate,
            "typical_bitrate": self.typical_bitrate,
            "max_bitrate": self.max_bitrate,
            "payload_type": self.payload_type,
            "available": self.speex_available,
            "features": features,
        }

    def get_sdp_description(self) -> str:
        """
        Get SDP description for Speex codec

        Returns:
            str: SDP rtpmap attribute
        """
        # Speex SDP format: rtpmap:<pt> SPEEX/<sample_rate>
        return f"rtpmap:{self.payload_type} SPEEX/{self.sample_rate}"

    def get_fmtp(self) -> str | None:
        """
        Get SDP fmtp (format parameters) for Speex

        Returns:
            str: SDP fmtp attribute with codec parameters, or None
        """
        # Build fmtp parameters
        params = []

        if self.vbr_enabled:
            params.append("vbr=on")

        # Mode parameter for wideband/ultra-wideband
        if self.mode == self.MODE_WIDEBAND:
            params.append('mode="1,any"')  # Wideband
        elif self.mode == self.MODE_ULTRA_WIDEBAND:
            params.append('mode="2,any"')  # Ultra-wideband

        if params:
            return f"fmtp:{self.payload_type} {';'.join(params)}"
        return None

    def get_sdp_parameters(self) -> dict[str, Any]:
        """
        Get complete SDP parameters

        Returns:
            dict with SDP negotiation parameters
        """
        params = {
            "payload_type": self.payload_type,
            "encoding_name": "SPEEX",
            "clock_rate": self.sample_rate,
            "channels": 1,
            "mode": self.mode,
            "rtpmap": self.get_sdp_description(),
        }

        fmtp = self.get_fmtp()
        if fmtp:
            params["fmtp"] = fmtp

        return params

    def create_encoder(self) -> Any:
        """
        Create Speex encoder

        This initializes the encoder state for encoding PCM to Speex.
        """
        if not self.speex_available:
            self.logger.warning("Cannot create encoder - speex not available")
            return

        try:
            import speex

            # Create encoder based on mode
            if self.mode == self.MODE_NARROWBAND:
                self.encoder = speex.NBEncoder()  # Narrowband
            elif self.mode == self.MODE_WIDEBAND:
                self.encoder = speex.WBEncoder()  # Wideband
            else:  # Ultra-wideband
                self.encoder = speex.UWBEncoder()  # Ultra-wideband

            # set encoder parameters
            if hasattr(self.encoder, "quality"):
                self.encoder.quality = self.quality
            if hasattr(self.encoder, "complexity"):
                self.encoder.complexity = self.complexity
            if hasattr(self.encoder, "vbr"):
                self.encoder.vbr = self.vbr_enabled
            if hasattr(self.encoder, "vad"):
                self.encoder.vad = self.vad_enabled
            if hasattr(self.encoder, "dtx"):
                self.encoder.dtx = self.dtx_enabled

            self.logger.debug(f"Speex encoder created (mode: {self.mode}, quality: {self.quality})")
        except Exception as e:
            self.logger.error(f"Failed to create Speex encoder: {e}")
            self.encoder = None

    def create_decoder(self) -> Any:
        """
        Create Speex decoder

        This initializes the decoder state for decoding Speex to PCM.
        """
        if not self.speex_available:
            self.logger.warning("Cannot create decoder - speex not available")
            return

        try:
            import speex

            # Create decoder based on mode
            if self.mode == self.MODE_NARROWBAND:
                self.decoder = speex.NBDecoder()  # Narrowband
            elif self.mode == self.MODE_WIDEBAND:
                self.decoder = speex.WBDecoder()  # Wideband
            else:  # Ultra-wideband
                self.decoder = speex.UWBDecoder()  # Ultra-wideband

            self.logger.debug(f"Speex decoder created (mode: {self.mode})")
        except Exception as e:
            self.logger.error(f"Failed to create Speex decoder: {e}")
            self.decoder = None

    def encode(self, pcm_data: bytes) -> bytes | None:
        """
        Encode PCM audio to Speex

        Args:
            pcm_data: Raw PCM audio data (16-bit signed, mono, matching sample rate)
                     Should be frame_size samples

        Returns:
            bytes: Encoded Speex data, or None on error
        """
        if not self.encoder:
            self.logger.warning("Encoder not initialized - call create_encoder() first")
            return None

        # Verify input size
        expected_bytes = self.frame_size * 2  # 16-bit samples
        if len(pcm_data) != expected_bytes:
            self.logger.error(
                f"Invalid PCM data size: got {len(pcm_data)}, expected {expected_bytes} bytes"
            )
            return None

        try:
            # Encode PCM to Speex
            encoded = self.encoder.encode(pcm_data)
            return encoded
        except Exception as e:
            self.logger.error(f"Speex encoding failed: {e}")
            return None

    def decode(self, speex_data: bytes) -> bytes | None:
        """
        Decode Speex audio to PCM

        Args:
            speex_data: Encoded Speex data

        Returns:
            bytes: Decoded PCM audio (16-bit signed, mono), or None on error
        """
        if not self.decoder:
            self.logger.warning("Decoder not initialized - call create_decoder() first")
            return None

        try:
            # Decode Speex to PCM
            decoded = self.decoder.decode(speex_data)
            return decoded
        except Exception as e:
            self.logger.error(f"Speex decoding failed: {e}")
            return None

    def reset_encoder(self) -> None:
        """Reset encoder state"""
        if self.encoder:
            self.create_encoder()  # Recreate encoder

    def reset_decoder(self) -> None:
        """Reset decoder state"""
        if self.decoder:
            self.create_decoder()  # Recreate decoder


class SpeexCodecManager:
    """
    Manager for Speex codec instances

    Manages multiple Speex codec instances for different calls.
    """

    def __init__(self, pbx: Any) -> None:
        """
        Initialize Speex codec manager

        Args:
            pbx: PBX instance
        """
        self.pbx = pbx
        self.logger = get_logger()
        self.codecs = {}  # call_id -> SpeexCodec

        # Get global config
        self.config = {}
        if hasattr(pbx, "config") and pbx.config:
            codec_config = pbx.config.get("codecs", {})
            self.config = codec_config.get("speex", {})

        self.logger.info("Speex codec manager initialized")

    def create_codec(self, call_id: str, config: dict[str, Any] | None = None) -> SpeexCodec:
        """
        Create Speex codec instance for a call

        Args:
            call_id: Unique call identifier
            config: Optional codec configuration (uses global config if not provided)

        Returns:
            SpeexCodec instance
        """
        # Use provided config or global config
        codec_config = config or self.config

        # Create codec instance
        codec = SpeexCodec(codec_config)
        self.codecs[call_id] = codec

        self.logger.debug(f"Created Speex codec for call {call_id}")
        return codec

    def get_codec(self, call_id: str) -> SpeexCodec | None:
        """
        Get codec instance for a call

        Args:
            call_id: Call identifier

        Returns:
            SpeexCodec instance or None
        """
        return self.codecs.get(call_id)

    def remove_codec(self, call_id: str) -> None:
        """
        Remove codec instance for a call

        Args:
            call_id: Call identifier
        """
        if call_id in self.codecs:
            del self.codecs[call_id]
            self.logger.debug(f"Removed Speex codec for call {call_id}")

    def get_all_codecs(self) -> dict[str, SpeexCodec]:
        """
        Get all codec instances

        Returns:
            dict mapping call_id to SpeexCodec
        """
        return self.codecs.copy()

    def is_speex_available(self) -> bool:
        """
        Check if Speex is available system-wide

        Returns:
            bool: True if speex library is available
        """
        try:
            return True
        except ImportError:
            return False
