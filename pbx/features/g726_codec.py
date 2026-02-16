"""
G.726 Codec Support
ITU-T G.726 is an ADPCM speech codec with multiple bitrate variants.

This module provides G.726 codec negotiation and integration with the PBX
system.  Encoding and decoding for G.726-32 (4 bits per sample) is handled
by a pure-Python IMA ADPCM implementation that is compatible with the
algorithm formerly provided by the removed ``audioop`` standard-library
module.

Supports all G.726 bitrate variants:
- G.726-16: 16 kbit/s (2 bits per sample)
- G.726-24: 24 kbit/s (3 bits per sample)
- G.726-32: 32 kbit/s (4 bits per sample) - most common, also known as G721
- G.726-40: 40 kbit/s (5 bits per sample)
"""

import struct
from typing import ClassVar

from pbx.utils.logger import get_logger

# ---------------------------------------------------------------------------
# IMA ADPCM tables (identical to the tables used by CPython's audioop)
# ---------------------------------------------------------------------------

# Step-size index adjustment table, indexed by the ADPCM code (0..7 for the
# magnitude portion of each nibble).
_INDEX_TABLE: list[int] = [
    -1,
    -1,
    -1,
    -1,
    2,
    4,
    6,
    8,
]

# Quantiser step-size table, indexed by the step-size index (0..88).
_STEP_SIZE_TABLE: list[int] = [
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    16,
    17,
    19,
    21,
    23,
    25,
    28,
    31,
    34,
    37,
    41,
    45,
    50,
    55,
    60,
    66,
    73,
    80,
    88,
    97,
    107,
    118,
    130,
    143,
    157,
    173,
    190,
    209,
    230,
    253,
    279,
    307,
    337,
    371,
    408,
    449,
    494,
    544,
    598,
    658,
    724,
    796,
    876,
    963,
    1060,
    1166,
    1282,
    1411,
    1552,
    1707,
    1878,
    2066,
    2272,
    2499,
    2749,
    3024,
    3327,
    3660,
    4026,
    4428,
    4871,
    5358,
    5894,
    6484,
    7132,
    7845,
    8630,
    9493,
    10442,
    11487,
    12635,
    13899,
    15289,
    16818,
    18500,
    20350,
    22385,
    24623,
    27086,
    29794,
    32767,
]


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp *value* to the closed interval [*lo*, *hi*]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


# ---------------------------------------------------------------------------
# Pure-Python IMA ADPCM encoder / decoder
# ---------------------------------------------------------------------------
# These two functions replicate the behaviour of the (now removed)
# ``audioop.lin2adpcm`` and ``audioop.adpcm2lin`` functions from CPython so
# that existing callers continue to work without modification.
# ---------------------------------------------------------------------------


def _ima_adpcm_encode(
    pcm_data: bytes, state: tuple[int, int] | None = None
) -> tuple[bytes, tuple[int, int]]:
    """Encode 16-bit signed LE PCM data to 4-bit IMA ADPCM.

    Args:
        pcm_data: Raw 16-bit signed little-endian PCM bytes.
        state: Optional ``(predicted_value, step_index)`` tuple carried over
            from a previous call.  Pass ``None`` to start fresh.

    Returns:
        A ``(adpcm_bytes, new_state)`` tuple.  Each output byte packs two
        4-bit ADPCM nibbles (first sample in the low nibble, second in the
        high nibble), matching the layout produced by CPython's ``audioop``.
    """
    if state is None:
        predicted: int = 0
        index: int = 0
    else:
        predicted, index = state

    num_samples = len(pcm_data) // 2
    output = bytearray()
    buffered_nibble: int = -1  # -1 means "no nibble waiting"

    for i in range(num_samples):
        sample = struct.unpack_from("<h", pcm_data, i * 2)[0]
        step = _STEP_SIZE_TABLE[index]

        # Compute difference from prediction
        diff = sample - predicted

        # Encode sign
        if diff < 0:
            nibble = 8  # sign bit
            diff = -diff
        else:
            nibble = 0

        # Quantise magnitude into 3 bits
        mask = 4
        temp_step = step
        for _ in range(3):
            if diff >= temp_step:
                nibble |= mask
                diff -= temp_step
            temp_step >>= 1
            mask >>= 1

        # Decode the nibble back to update predicted value (keeps encoder and
        # decoder in sync).
        code = nibble & 0x07
        delta = step >> 3
        if code & 4:
            delta += step
        if code & 2:
            delta += step >> 1
        if code & 1:
            delta += step >> 2

        if nibble & 8:
            predicted -= delta
        else:
            predicted += delta

        predicted = _clamp(predicted, -32768, 32767)

        # Update step index
        index = _clamp(index + _INDEX_TABLE[code], 0, 88)

        # Pack two nibbles per byte (low nibble first, then high)
        if buffered_nibble < 0:
            buffered_nibble = nibble & 0x0F
        else:
            output.append(buffered_nibble | ((nibble & 0x0F) << 4))
            buffered_nibble = -1

    # If an odd number of samples, flush the remaining nibble
    if buffered_nibble >= 0:
        output.append(buffered_nibble)

    return bytes(output), (predicted, index)


def _ima_adpcm_decode(
    adpcm_data: bytes, sample_width: int, state: tuple[int, int] | None = None
) -> tuple[bytes, tuple[int, int]]:
    """Decode 4-bit IMA ADPCM to 16-bit signed LE PCM data.

    Args:
        adpcm_data: ADPCM encoded bytes (two nibbles per byte, low nibble
            first).
        sample_width: Output sample width in bytes.  Must be ``2`` (16-bit).
        state: Optional ``(predicted_value, step_index)`` tuple carried over
            from a previous call.  Pass ``None`` to start fresh.

    Returns:
        A ``(pcm_bytes, new_state)`` tuple.
    """
    if sample_width != 2:
        raise ValueError(f"Only 16-bit (sample_width=2) output is supported, got {sample_width}")

    if state is None:
        predicted: int = 0
        index: int = 0
    else:
        predicted, index = state

    output = bytearray()

    for byte in adpcm_data:
        # Each byte contains two nibbles: low nibble is the first sample
        for shift in (0, 4):
            nibble = (byte >> shift) & 0x0F

            step = _STEP_SIZE_TABLE[index]
            code = nibble & 0x07

            # Reconstruct difference
            delta = step >> 3
            if code & 4:
                delta += step
            if code & 2:
                delta += step >> 1
            if code & 1:
                delta += step >> 2

            if nibble & 8:
                predicted -= delta
            else:
                predicted += delta

            predicted = _clamp(predicted, -32768, 32767)

            # Update step index
            index = _clamp(index + _INDEX_TABLE[code], 0, 88)

            output.extend(struct.pack("<h", predicted))

    return bytes(output), (predicted, index)


# ---------------------------------------------------------------------------
# G.726 codec class
# ---------------------------------------------------------------------------


class G726Codec:
    """
    G.726 ADPCM codec implementation

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
    PAYLOAD_TYPES: ClassVar[dict[int, int | None]] = {
        16: None,  # No static type, use dynamic (96-127)
        24: None,  # No static type, use dynamic (96-127)
        32: 2,  # G721 (G.726-32) - standard static type
        40: None,  # No static type, use dynamic (96-127)
    }

    # Default dynamic payload types (when static not available)
    DEFAULT_DYNAMIC_TYPES: ClassVar[dict[int, int]] = {16: 112, 24: 113, 32: 2, 40: 114}

    # Bits per sample for each bitrate
    BITS_PER_SAMPLE: ClassVar[dict[int, int]] = {16: 2, 24: 3, 32: 4, 40: 5}

    def __init__(self, bitrate: int = 32000) -> None:
        """
        Initialize G.726 codec.

        Args:
            bitrate: Bitrate in bits per second (16000, 24000, 32000, or 40000).

        Raises:
            ValueError: If bitrate is not supported.
        """
        self.logger = get_logger()

        # Convert bitrate to kbit/s for easier handling
        self.bitrate_kbps = bitrate // 1000

        if self.bitrate_kbps not in (16, 24, 32, 40):
            raise ValueError(
                f"Unsupported G.726 bitrate: {bitrate}. Must be 16000, 24000, 32000, or 40000"
            )

        self.bitrate = bitrate
        self.bits_per_sample = self.BITS_PER_SAMPLE[self.bitrate_kbps]
        self.payload_type = self.DEFAULT_DYNAMIC_TYPES[self.bitrate_kbps]
        self.enabled = True

        self.logger.debug(
            f"G.726 codec initialized at {self.bitrate_kbps} kbit/s "
            f"({self.bits_per_sample} bits/sample)"
        )

        # Internal ADPCM state carried across successive encode/decode calls
        self._encode_state: tuple[int, int] | None = None
        self._decode_state: tuple[int, int] | None = None

    def encode(self, pcm_data: bytes) -> bytes | None:
        """
        Encode PCM audio to G.726 ADPCM.

        Args:
            pcm_data: Raw PCM audio data (16-bit signed, 8 kHz, little-endian).

        Returns:
            Encoded G.726 data, or ``None`` if encoding fails.
        """
        try:
            if self.bitrate_kbps == 32:
                adpcm_data, self._encode_state = _ima_adpcm_encode(
                    pcm_data,
                    self._encode_state,
                )
                return adpcm_data
            # For 16, 24, 40 kbit/s variants a specialised library is needed
            self.logger.warning(
                f"G.726-{self.bitrate_kbps} encoding not implemented. Only G.726-32 is supported."
            )
            return None
        except Exception as e:
            self.logger.error(f"G.726 encoding error: {e}")
            return None

    def decode(self, g726_data: bytes) -> bytes | None:
        """
        Decode G.726 ADPCM to PCM audio.

        Args:
            g726_data: Encoded G.726 data.

        Returns:
            Decoded PCM audio data (16-bit signed, 8 kHz, little-endian), or
            ``None`` if decoding fails.
        """
        try:
            if len(g726_data) == 0:
                return b""

            if self.bitrate_kbps == 32:
                pcm_data, self._decode_state = _ima_adpcm_decode(
                    g726_data,
                    2,
                    self._decode_state,
                )
                return pcm_data
            # For 16, 24, 40 kbit/s variants a specialised library is needed
            self.logger.warning(
                f"G.726-{self.bitrate_kbps} decoding not implemented. Only G.726-32 is supported."
            )
            return None
        except Exception as e:
            self.logger.error(f"G.726 decoding error: {e}")
            return None

    def get_info(self) -> dict:
        """
        Get codec information.

        Returns:
            Dictionary with codec details.
        """
        impl_status = "Full (pure Python ADPCM)" if self.bitrate_kbps == 32 else "Framework Only"

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
        """Get quality description for current bitrate."""
        quality_map = {
            16: "Fair (Narrowband, High Compression)",
            24: "Good (Narrowband, Good Compression)",
            32: "Good (Narrowband, Moderate Compression)",
            40: "Very Good (Narrowband, Low Compression)",
        }
        return quality_map.get(self.bitrate_kbps, "Unknown")

    def get_sdp_description(self) -> str:
        """
        Get SDP format description for SIP negotiation.

        Returns:
            SDP media format string.
        """
        # G.726 uses 8000 Hz sample rate with one channel
        # Different naming conventions:
        # - G726-32 is sometimes called G721 or AAL2-G726-32
        # - Some implementations use G726-XX format

        if self.bitrate_kbps == 32:
            # G.726-32 can also be advertised as G721
            return f"rtpmap:{self.payload_type} G726-32/{self.SAMPLE_RATE}"
        return f"rtpmap:{self.payload_type} G726-{self.bitrate_kbps}/{self.SAMPLE_RATE}"

    def get_fmtp_params(self) -> str | None:
        """
        Get format parameters for SDP.

        Returns:
            FMTP parameter string or ``None``.
        """
        # G.726 typically doesn't require fmtp parameters
        # Some implementations may specify bitrate explicitly
        return None

    @staticmethod
    def is_supported(bitrate: int = 32000) -> bool:
        """
        Check if G.726 codec is supported for given bitrate.

        Args:
            bitrate: Bitrate to check (16000, 24000, 32000, or 40000).

        Returns:
            ``True`` if codec is available for this bitrate.
        """
        bitrate_kbps = bitrate // 1000

        # G.726-32 is fully supported via the pure-Python ADPCM implementation
        # Other bitrates would need a specialised library
        return bitrate_kbps == 32

    @staticmethod
    def get_capabilities() -> dict:
        """
        Get codec capabilities.

        Returns:
            Dictionary with supported features.
        """
        return {
            "bitrates": [16000, 24000, 32000, 40000],
            "sample_rate": 8000,
            "channels": 1,  # Mono
            "bits_per_sample": [2, 3, 4, 5],
            "complexity": "Low",
            "latency": "Very Low",
            "applications": ["VoIP", "Telephony", "Low-bandwidth scenarios"],
            "note": "G.726-32 fully supported via pure-Python ADPCM, others framework only",
        }


class G726CodecManager:
    """
    Manager for G.726 codec instances and configuration.
    """

    def __init__(self, config: dict | None = None) -> None:
        """
        Initialize G.726 codec manager.

        Args:
            config: Configuration dictionary.
        """
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get("codecs.g726.enabled", False)
        self.default_bitrate = self.config.get("codecs.g726.bitrate", 32000)

        # Validate bitrate
        if self.default_bitrate not in (16000, 24000, 32000, 40000):
            self.logger.warning(
                f"Invalid G.726 bitrate {self.default_bitrate}, defaulting to 32000"
            )
            self.default_bitrate = 32000

        # Codec instances cache
        self.encoders: dict[str, G726Codec] = {}  # call_id -> encoder instance
        self.decoders: dict[str, G726Codec] = {}  # call_id -> decoder instance

        if self.enabled:
            bitrate_kbps = self.default_bitrate // 1000
            self.logger.info(f"G.726 codec manager initialized (bitrate: {bitrate_kbps} kbit/s)")

            if not G726Codec.is_supported(self.default_bitrate):
                self.logger.warning(
                    f"G.726-{bitrate_kbps} encoding/decoding is not supported. "
                    "Only G.726-32 has full support."
                )
        else:
            self.logger.info("G.726 codec disabled in configuration")

    def create_encoder(self, call_id: str, bitrate: int | None = None) -> G726Codec | None:
        """
        Create encoder for a call.

        Args:
            call_id: Call identifier.
            bitrate: Optional bitrate (defaults to config).

        Returns:
            G726Codec instance or ``None``.
        """
        if not self.enabled:
            return None

        bitrate = bitrate or self.default_bitrate
        encoder = G726Codec(bitrate=bitrate)
        self.encoders[call_id] = encoder

        self.logger.debug(f"Created G.726 encoder for call {call_id}")
        return encoder

    def create_decoder(self, call_id: str, bitrate: int | None = None) -> G726Codec | None:
        """
        Create decoder for a call.

        Args:
            call_id: Call identifier.
            bitrate: Optional bitrate (defaults to config).

        Returns:
            G726Codec instance or ``None``.
        """
        if not self.enabled:
            return None

        bitrate = bitrate or self.default_bitrate
        decoder = G726Codec(bitrate=bitrate)
        self.decoders[call_id] = decoder

        self.logger.debug(f"Created G.726 decoder for call {call_id}")
        return decoder

    def release_codec(self, call_id: str) -> None:
        """
        Release codec resources for a call.

        Args:
            call_id: Call identifier.
        """
        if call_id in self.encoders:
            del self.encoders[call_id]

        if call_id in self.decoders:
            del self.decoders[call_id]

        self.logger.debug(f"Released G.726 codecs for call {call_id}")

    def get_encoder(self, call_id: str) -> G726Codec | None:
        """Get encoder for a call."""
        return self.encoders.get(call_id)

    def get_decoder(self, call_id: str) -> G726Codec | None:
        """Get decoder for a call."""
        return self.decoders.get(call_id)

    def get_statistics(self) -> dict:
        """
        Get codec usage statistics.

        Returns:
            Dictionary with statistics.
        """
        return {
            "enabled": self.enabled,
            "default_bitrate": self.default_bitrate,
            "active_encoders": len(self.encoders),
            "active_decoders": len(self.decoders),
            "supported": G726Codec.is_supported(self.default_bitrate),
        }

    def get_sdp_capabilities(self) -> list[str]:
        """
        Get SDP capabilities for SIP negotiation.

        Returns:
            list of SDP format lines.
        """
        if not self.enabled:
            return []

        codec = G726Codec(self.default_bitrate)
        capabilities = [f"a={codec.get_sdp_description()}"]

        fmtp = codec.get_fmtp_params()
        if fmtp:
            capabilities.append(f"a={fmtp}")

        return capabilities
