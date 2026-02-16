"""
Opus Codec Support
Provides support for Opus audio codec (RFC 6716, 7587)
Opus is a modern, high-quality, low-latency audio codec
"""

from typing import Any

from pbx.utils.logger import get_logger


class OpusCodec:
    """
    Opus codec handler for the PBX system

    Opus (RFC 6716) is a versatile audio codec that adapts to:
    - Bitrates from 6 kbit/s to 510 kbit/s
    - Sample rates from 8 kHz to 48 kHz
    - Both speech and music
    - Low latency (5-60 ms)
    """

    # Opus payload type (typically 96-127 for dynamic types)
    PAYLOAD_TYPE = 111

    # Opus codec parameters
    SAMPLE_RATES = [8000, 12000, 16000, 24000, 48000]  # Supported sample rates
    DEFAULT_SAMPLE_RATE = 48000  # Hz
    DEFAULT_BITRATE = 32000  # 32 kbit/s (good quality for VoIP)
    DEFAULT_FRAME_SIZE = 20  # milliseconds
    DEFAULT_CHANNELS = 1  # Mono for telephony

    # Application types
    APP_VOIP = 2048  # Optimize for voice
    APP_AUDIO = 2049  # Optimize for music
    APP_LOWDELAY = 2051  # Optimize for low latency

    # Complexity levels (0-10, where 10 is highest quality)
    DEFAULT_COMPLEXITY = 5  # Balance between quality and CPU

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize Opus codec handler

        Args:
            config: Optional configuration dictionary with:
                - sample_rate: Audio sample rate (default: 48000 Hz)
                - bitrate: Target bitrate (default: 32000 bps)
                - frame_size: Frame duration in ms (default: 20 ms)
                - channels: Number of channels (default: 1 for mono)
                - application: Application type (voip, audio, lowdelay)
                - complexity: Encoding complexity 0-10 (default: 5)
                - fec: Enable forward error correction (default: True)
                - dtx: Enable discontinuous transmission (default: False)
        """
        self.logger = get_logger()
        self.config = config or {}

        # Codec parameters
        self.sample_rate = self.config.get("sample_rate", self.DEFAULT_SAMPLE_RATE)
        self.bitrate = self.config.get("bitrate", self.DEFAULT_BITRATE)
        self.frame_size = self.config.get("frame_size", self.DEFAULT_FRAME_SIZE)
        self.channels = self.config.get("channels", self.DEFAULT_CHANNELS)
        self.complexity = self.config.get("complexity", self.DEFAULT_COMPLEXITY)

        # Application type
        app_type = self.config.get("application", "voip")
        if app_type == "audio":
            self.application = self.APP_AUDIO
        elif app_type == "lowdelay":
            self.application = self.APP_LOWDELAY
        else:
            self.application = self.APP_VOIP

        # Features
        self.fec_enabled = self.config.get("fec", True)  # Forward Error Correction
        self.dtx_enabled = self.config.get("dtx", False)  # Discontinuous Transmission

        # Validation
        if self.sample_rate not in self.SAMPLE_RATES:
            self.logger.warning(
                f"Invalid sample rate {self.sample_rate}, using {self.DEFAULT_SAMPLE_RATE}"
            )
            self.sample_rate = self.DEFAULT_SAMPLE_RATE

        if not 6000 <= self.bitrate <= 510000:
            self.logger.warning(f"Invalid bitrate {self.bitrate}, using {self.DEFAULT_BITRATE}")
            self.bitrate = self.DEFAULT_BITRATE

        if self.complexity < 0 or self.complexity > 10:
            self.logger.warning(
                f"Invalid complexity {self.complexity}, using {self.DEFAULT_COMPLEXITY}"
            )
            self.complexity = self.DEFAULT_COMPLEXITY

        # Try to import opus library
        self.opus_available = False
        try:
            import opuslib

            self.opuslib = opuslib
            self.opus_available = True
            self.logger.info("Opus codec library available")
        except ImportError:
            self.logger.warning("opuslib not available. Install with: pip install opuslib")
            self.logger.info("Opus codec support will be limited to SDP negotiation only")

        # Encoder and decoder (created on demand)
        self.encoder = None
        self.decoder = None

        self.logger.info(
            f"Opus codec initialized: {self.sample_rate}Hz, {self.bitrate}bps, {self.frame_size}ms frames"
        )

    def is_available(self) -> bool:
        """
        Check if Opus codec library is available

        Returns:
            True if opuslib is installed and functional
        """
        return self.opus_available

    def get_sdp_parameters(self) -> dict[str, Any]:
        """
        Get SDP parameters for Opus codec

        Returns:
            Dictionary with SDP media attributes
        """
        # RFC 7587 - RTP Payload Format for Opus
        return {
            "payload_type": self.PAYLOAD_TYPE,
            "encoding_name": "opus",
            "clock_rate": 48000,  # Opus always uses 48kHz clock rate in RTP
            "channels": self.channels,
            "fmtp": self._build_fmtp_string(),
        }

    def _build_fmtp_string(self) -> str:
        """
        Build format parameters (fmtp) string for SDP

        Returns:
            fmtp string (e.g., "minptime=10; useinbandfec=1")
        """
        params = []

        # Minimum packet time
        params.append(f"minptime={self.frame_size}")

        # Forward Error Correction
        if self.fec_enabled:
            params.append("useinbandfec=1")

        # Discontinuous Transmission
        if self.dtx_enabled:
            params.append("usedtx=1")

        # Maximum average bitrate
        params.append(f"maxaveragebitrate={self.bitrate}")

        return "; ".join(params)

    def create_encoder(self) -> Any:
        """
        Create Opus encoder instance

        Returns:
            Opus encoder object or None if library not available
        """
        if not self.opus_available:
            self.logger.warning("Cannot create encoder: opuslib not available")
            return None

        try:
            from opuslib import Encoder

            # Calculate frame samples
            int(self.sample_rate * self.frame_size / 1000)

            self.encoder = Encoder(
                fs=self.sample_rate, channels=self.channels, application=self.application
            )

            # Configure encoder
            self.encoder.bitrate = self.bitrate
            self.encoder.complexity = self.complexity
            self.encoder.fec = 1 if self.fec_enabled else 0
            self.encoder.dtx = 1 if self.dtx_enabled else 0

            self.logger.info(f"Opus encoder created: {self.sample_rate}Hz, {self.bitrate}bps")
            return self.encoder
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to create Opus encoder: {e}")
            return None

    def create_decoder(self) -> Any:
        """
        Create Opus decoder instance

        Returns:
            Opus decoder object or None if library not available
        """
        if not self.opus_available:
            self.logger.warning("Cannot create decoder: opuslib not available")
            return None

        try:
            from opuslib import Decoder

            self.decoder = Decoder(fs=self.sample_rate, channels=self.channels)

            self.logger.info(f"Opus decoder created: {self.sample_rate}Hz")
            return self.decoder
        except Exception as e:
            self.logger.error(f"Failed to create Opus decoder: {e}")
            return None

    def encode(self, pcm_data: bytes) -> bytes | None:
        """
        Encode PCM audio data to Opus

        Args:
            pcm_data: Raw PCM audio data (16-bit signed integers)

        Returns:
            Encoded Opus packet or None on error
        """
        if not self.encoder:
            self.create_encoder()

        if not self.encoder:
            return None

        try:
            # Calculate frame size in samples
            frame_samples = int(self.sample_rate * self.frame_size / 1000)
            expected_bytes = frame_samples * self.channels * 2  # 2 bytes per sample (16-bit)

            if len(pcm_data) != expected_bytes:
                self.logger.warning(
                    f"PCM data size mismatch: got {len(pcm_data)}, expected {expected_bytes}"
                )
                return None

            # Encode the frame
            encoded = self.encoder.encode(pcm_data, frame_samples)
            return encoded
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Opus encoding error: {e}")
            return None

    def decode(self, opus_data: bytes, frame_size: int | None = None) -> bytes | None:
        """
        Decode Opus data to PCM audio

        Args:
            opus_data: Encoded Opus packet
            frame_size: Frame size in samples (optional, uses default if not specified)

        Returns:
            Decoded PCM audio data or None on error
        """
        if not self.decoder:
            self.create_decoder()

        if not self.decoder:
            return None

        try:
            # Use configured frame size if not specified
            if frame_size is None:
                frame_size = int(self.sample_rate * self.frame_size / 1000)

            # Decode the packet
            decoded = self.decoder.decode(opus_data, frame_size)
            return decoded
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Opus decoding error: {e}")
            return None

    def handle_packet_loss(self, frame_size: int | None = None) -> bytes | None:
        """
        Generate concealment audio for lost packet (Packet Loss Concealment)

        Args:
            frame_size: Frame size in samples (optional, uses default if not specified)

        Returns:
            Concealment audio data or None on error
        """
        if not self.decoder:
            return None

        try:
            # Use configured frame size if not specified
            if frame_size is None:
                frame_size = int(self.sample_rate * self.frame_size / 1000)

            # Opus can generate concealment audio without encoded data
            # Pass None as the packet to trigger PLC
            concealment = self.decoder.decode(None, frame_size, decode_fec=False)
            return concealment
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Opus PLC error: {e}")
            return None

    def decode_with_fec(self, opus_data: bytes, frame_size: int | None = None) -> bytes | None:
        """
        Decode Opus data with Forward Error Correction

        Args:
            opus_data: Encoded Opus packet from next frame (contains FEC for current)
            frame_size: Frame size in samples (optional, uses default if not specified)

        Returns:
            Decoded FEC audio data or None on error
        """
        if not self.decoder or not self.fec_enabled:
            return None

        try:
            # Use configured frame size if not specified
            if frame_size is None:
                frame_size = int(self.sample_rate * self.frame_size / 1000)

            # Decode FEC from the next packet
            fec_audio = self.decoder.decode(opus_data, frame_size, decode_fec=True)
            return fec_audio
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Opus FEC decoding error: {e}")
            return None

    def reset_encoder(self) -> None:
        """Reset encoder state"""
        if self.encoder:
            try:
                self.encoder.reset_state()
                self.logger.debug("Opus encoder state reset")
            except Exception as e:
                self.logger.error(f"Failed to reset encoder: {e}")

    def reset_decoder(self) -> None:
        """Reset decoder state"""
        if self.decoder:
            try:
                self.decoder.reset_state()
                self.logger.debug("Opus decoder state reset")
            except Exception as e:
                self.logger.error(f"Failed to reset decoder: {e}")

    def get_info(self) -> dict[str, Any]:
        """
        Get codec information and current configuration

        Returns:
            Dictionary with codec details
        """
        return {
            "name": "Opus",
            "rfc": "RFC 6716, RFC 7587",
            "available": self.opus_available,
            "configuration": {
                "sample_rate": self.sample_rate,
                "bitrate": self.bitrate,
                "frame_size_ms": self.frame_size,
                "channels": self.channels,
                "complexity": self.complexity,
                "application": self._get_app_name(),
                "fec_enabled": self.fec_enabled,
                "dtx_enabled": self.dtx_enabled,
            },
            "sdp": self.get_sdp_parameters(),
            "encoder_ready": self.encoder is not None,
            "decoder_ready": self.decoder is not None,
        }

    def _get_app_name(self) -> str:
        """Get application type name"""
        if self.application == self.APP_AUDIO:
            return "audio"
        if self.application == self.APP_LOWDELAY:
            return "lowdelay"
        return "voip"


class OpusCodecManager:
    """
    Manages Opus codecs for multiple calls
    """

    def __init__(self, pbx: Any) -> None:
        """
        Initialize Opus codec manager

        Args:
            pbx: Reference to main PBX instance
        """
        self.pbx = pbx
        self.logger = get_logger()
        self.codecs = {}  # call_id -> OpusCodec

        # Get global configuration
        self.config = pbx.config.get("codecs.opus", {})

        self.logger.info("Opus codec manager initialized")

    def create_codec(self, call_id: str, config: dict[str, Any] | None = None) -> OpusCodec:
        """
        Create Opus codec for a call

        Args:
            call_id: Unique call identifier
            config: Optional codec configuration (uses global config if not specified)

        Returns:
            OpusCodec instance
        """
        # Merge call-specific config with global config
        codec_config = {**self.config, **(config or {})}

        codec = OpusCodec(codec_config)
        self.codecs[call_id] = codec

        self.logger.info(f"Created Opus codec for call {call_id}")
        return codec

    def get_codec(self, call_id: str) -> OpusCodec | None:
        """
        Get Opus codec for a call

        Args:
            call_id: Unique call identifier

        Returns:
            OpusCodec instance or None if not found
        """
        return self.codecs.get(call_id)

    def remove_codec(self, call_id: str) -> None:
        """
        Remove Opus codec for a call

        Args:
            call_id: Unique call identifier
        """
        if call_id in self.codecs:
            del self.codecs[call_id]
            self.logger.info(f"Removed Opus codec for call {call_id}")

    def get_all_codecs(self) -> dict[str, OpusCodec]:
        """
        Get all active codecs

        Returns:
            Dictionary of call_id -> OpusCodec
        """
        return self.codecs.copy()

    def is_opus_available(self) -> bool:
        """
        Check if Opus library is available

        Returns:
            True if opuslib is installed
        """
        try:
            return True
        except ImportError:
            return False
