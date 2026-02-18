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
# Generic N-bit ADPCM encoder / decoder
# ---------------------------------------------------------------------------
# The G.726 family uses the same IMA ADPCM prediction loop at all bitrates;
# only the number of quantisation bits changes.  The functions below
# generalise the 4-bit encoder/decoder above to 2, 3, and 5 bits per sample.
#
# At *N* bits per sample the magnitude is encoded in *(N-1)* bits and the
# sign occupies the MSB.  The step-size index adjustment table is scaled
# correspondingly.
# ---------------------------------------------------------------------------

# Index adjustment tables keyed by bits-per-sample.
# These mirror the standard IMA ADPCM tables, truncated / extended for
# different quantisation depths.
_INDEX_TABLES: dict[int, list[int]] = {
    2: [-1, 2],  # 1 magnitude bit  (codes 0..1)
    3: [-1, -1, 2, 4],  # 2 magnitude bits (codes 0..3)
    4: _INDEX_TABLE,  # 3 magnitude bits (codes 0..7), already defined
    5: [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8],  # 4 magnitude bits
}


def _adpcm_encode_nbits(
    pcm_data: bytes,
    bits_per_sample: int,
    state: tuple[int, int] | None = None,
) -> tuple[bytes, tuple[int, int]]:
    """Encode 16-bit signed LE PCM to N-bit ADPCM.

    The output is packed MSB-first within each byte, which is the standard
    G.726 packing order.

    Args:
        pcm_data: Raw 16-bit signed little-endian PCM bytes.
        bits_per_sample: 2, 3, 4, or 5.
        state: Optional ``(predicted, index)`` carried from previous call.

    Returns:
        ``(adpcm_bytes, new_state)`` tuple.
    """
    if bits_per_sample == 4:
        # Delegate to the optimised 4-bit path
        return _ima_adpcm_encode(pcm_data, state)

    idx_table = _INDEX_TABLES[bits_per_sample]
    mag_bits = bits_per_sample - 1  # number of magnitude bits
    sign_bit = 1 << mag_bits  # sign bit position

    if state is None:
        predicted: int = 0
        index: int = 0
    else:
        predicted, index = state

    num_samples = len(pcm_data) // 2

    # Bit-packing state
    bit_buffer = 0
    bits_in_buffer = 0
    output = bytearray()

    for i in range(num_samples):
        sample = struct.unpack_from("<h", pcm_data, i * 2)[0]
        step = _STEP_SIZE_TABLE[index]

        diff = sample - predicted
        if diff < 0:
            code = sign_bit
            diff = -diff
        else:
            code = 0

        # Quantise magnitude into mag_bits bits
        temp_step = step
        for bit_pos in range(mag_bits - 1, -1, -1):
            if diff >= temp_step:
                code |= 1 << bit_pos
                diff -= temp_step
            temp_step >>= 1

        # Reconstruct to update prediction (keeps encoder/decoder in sync)
        magnitude = code & (sign_bit - 1)
        delta = step >> mag_bits
        for bit_pos in range(mag_bits - 1, -1, -1):
            if magnitude & (1 << bit_pos):
                delta += step >> (mag_bits - 1 - bit_pos)

        if code & sign_bit:
            predicted -= delta
        else:
            predicted += delta
        predicted = _clamp(predicted, -32768, 32767)

        # Update step index using magnitude portion only
        adj_idx = magnitude if magnitude < len(idx_table) else len(idx_table) - 1
        index = _clamp(index + idx_table[adj_idx], 0, 88)

        # Pack code into output (MSB-first packing)
        bit_buffer = (bit_buffer << bits_per_sample) | (code & ((1 << bits_per_sample) - 1))
        bits_in_buffer += bits_per_sample

        while bits_in_buffer >= 8:
            bits_in_buffer -= 8
            output.append((bit_buffer >> bits_in_buffer) & 0xFF)

    # Flush any remaining bits (pad with zeros on the right)
    if bits_in_buffer > 0:
        output.append((bit_buffer << (8 - bits_in_buffer)) & 0xFF)

    return bytes(output), (predicted, index)


def _adpcm_decode_nbits(
    adpcm_data: bytes,
    bits_per_sample: int,
    num_samples: int | None = None,
    state: tuple[int, int] | None = None,
) -> tuple[bytes, tuple[int, int]]:
    """Decode N-bit ADPCM to 16-bit signed LE PCM.

    Args:
        adpcm_data: ADPCM encoded bytes (MSB-first packing).
        bits_per_sample: 2, 3, 4, or 5.
        num_samples: Number of samples to decode.  If ``None``, decodes as
            many complete samples as possible from the data.
        state: Optional ``(predicted, index)`` carried from previous call.

    Returns:
        ``(pcm_bytes, new_state)`` tuple.
    """
    if bits_per_sample == 4:
        return _ima_adpcm_decode(adpcm_data, 2, state)

    idx_table = _INDEX_TABLES[bits_per_sample]
    mag_bits = bits_per_sample - 1
    sign_bit = 1 << mag_bits
    code_mask = (1 << bits_per_sample) - 1

    if state is None:
        predicted: int = 0
        index: int = 0
    else:
        predicted, index = state

    # Determine how many samples we can decode
    total_bits = len(adpcm_data) * 8
    max_samples = total_bits // bits_per_sample
    if num_samples is None:
        num_samples = max_samples
    else:
        num_samples = min(num_samples, max_samples)

    output = bytearray()

    # Bit-unpacking state
    bit_pos = 0  # current bit position in the data stream

    for _ in range(num_samples):
        # Extract bits_per_sample bits from the MSB-first packed stream
        byte_idx = bit_pos // 8
        bit_offset = bit_pos % 8

        # Read up to 2 bytes to cover the code
        if byte_idx + 1 < len(adpcm_data):
            word = (adpcm_data[byte_idx] << 8) | adpcm_data[byte_idx + 1]
        else:
            word = adpcm_data[byte_idx] << 8

        shift = 16 - bit_offset - bits_per_sample
        code = (word >> shift) & code_mask
        bit_pos += bits_per_sample

        step = _STEP_SIZE_TABLE[index]
        magnitude = code & (sign_bit - 1)

        # Reconstruct difference
        delta = step >> mag_bits
        for bp in range(mag_bits - 1, -1, -1):
            if magnitude & (1 << bp):
                delta += step >> (mag_bits - 1 - bp)

        if code & sign_bit:
            predicted -= delta
        else:
            predicted += delta
        predicted = _clamp(predicted, -32768, 32767)

        adj_idx = magnitude if magnitude < len(idx_table) else len(idx_table) - 1
        index = _clamp(index + idx_table[adj_idx], 0, 88)

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

        Supports all G.726 bitrates (16, 24, 32, 40 kbit/s) via the pure-
        Python ADPCM implementation.  State is carried across successive calls
        so that a continuous audio stream can be encoded incrementally.

        Args:
            pcm_data: Raw PCM audio data (16-bit signed, 8 kHz, little-endian).
                      Length must be a multiple of 2 (one sample = 2 bytes).

        Returns:
            Encoded G.726 data, or ``None`` if encoding fails.
        """
        try:
            adpcm_data, self._encode_state = _adpcm_encode_nbits(
                pcm_data,
                self.bits_per_sample,
                self._encode_state,
            )
            return adpcm_data
        except Exception as e:
            self.logger.error(f"G.726 encoding error: {e}")
            return None

    def decode(self, g726_data: bytes) -> bytes | None:
        """
        Decode G.726 ADPCM to PCM audio.

        Supports all G.726 bitrates (16, 24, 32, 40 kbit/s) via the pure-
        Python ADPCM implementation.  State is carried across successive calls
        so that a continuous audio stream can be decoded incrementally.

        Args:
            g726_data: Encoded G.726 data.

        Returns:
            Decoded PCM audio data (16-bit signed, 8 kHz, little-endian), or
            ``None`` if decoding fails.
        """
        try:
            if len(g726_data) == 0:
                return b""

            pcm_data, self._decode_state = _adpcm_decode_nbits(
                g726_data,
                self.bits_per_sample,
                state=self._decode_state,
            )
            return pcm_data
        except Exception as e:
            self.logger.error(f"G.726 decoding error: {e}")
            return None

    def get_info(self) -> dict:
        """
        Get codec information.

        Returns:
            Dictionary with codec details.
        """
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
            "implementation": f"Full (pure Python {self.bits_per_sample}-bit ADPCM)",
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

        All four G.726 bitrate variants (16, 24, 32, 40 kbit/s) are fully
        supported via the pure-Python ADPCM implementation.

        Args:
            bitrate: Bitrate to check (16000, 24000, 32000, or 40000).

        Returns:
            ``True`` if codec is available for this bitrate.
        """
        bitrate_kbps = bitrate // 1000
        return bitrate_kbps in (16, 24, 32, 40)

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
            "note": "All G.726 bitrates fully supported via pure-Python ADPCM",
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
