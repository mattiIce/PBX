"""
DTMF (Dual-Tone Multi-Frequency) Detection
Implements Goertzel algorithm for detecting telephone keypad tones
"""
import math
from typing import Optional, List
from pbx.utils.logger import get_logger

# DTMF frequency pairs for each key
DTMF_FREQUENCIES = {
    '1': (697, 1209), '2': (697, 1336), '3': (697, 1477), 'A': (697, 1633),
    '4': (770, 1209), '5': (770, 1336), '6': (770, 1477), 'B': (770, 1633),
    '7': (852, 1209), '8': (852, 1336), '9': (852, 1477), 'C': (852, 1633),
    '*': (941, 1209), '0': (941, 1336), '#': (941, 1477), 'D': (941, 1633)
}

# Standard DTMF frequencies
DTMF_LOW_FREQS = [697, 770, 852, 941]
DTMF_HIGH_FREQS = [1209, 1336, 1477, 1633]


class DTMFDetector:
    """DTMF tone detector using Goertzel algorithm"""

    def __init__(self, sample_rate: int = 8000, samples_per_frame: int = 205):
        """
        Initialize DTMF detector

        Args:
            sample_rate: Audio sample rate (Hz)
            samples_per_frame: Number of samples to analyze per frame
        """
        self.logger = get_logger()
        self.sample_rate = sample_rate
        self.samples_per_frame = samples_per_frame
        
        # Goertzel coefficients for each DTMF frequency
        self.coefficients = {}
        for freq in DTMF_LOW_FREQS + DTMF_HIGH_FREQS:
            # Calculate the nearest DFT bin for this frequency
            # 0.5 added for proper rounding to nearest integer
            k = int(round(samples_per_frame * freq / sample_rate))
            omega = (2.0 * math.pi * k) / samples_per_frame
            self.coefficients[freq] = 2.0 * math.cos(omega)
        
        self.logger.debug(f"DTMF detector initialized: {sample_rate}Hz, {samples_per_frame} samples/frame")

    def goertzel(self, samples: List[float], frequency: int) -> float:
        """
        Goertzel algorithm for detecting specific frequency

        Args:
            samples: Audio samples
            frequency: Target frequency to detect

        Returns:
            float: Magnitude of frequency component
        """
        coeff = self.coefficients[frequency]
        q1 = 0.0
        q2 = 0.0
        
        for sample in samples:
            # Goertzel difference equation
            q0 = coeff * q1 - q2 + sample
            q2 = q1
            q1 = q0
        
        # Calculate magnitude from final state
        magnitude = math.sqrt(q1 * q1 + q2 * q2 - q1 * q2 * coeff)
        return magnitude

    def detect_tone(self, samples: List[float], threshold: float = 0.3) -> Optional[str]:
        """
        Detect DTMF tone from audio samples

        Args:
            samples: Audio samples (should be samples_per_frame length)
            threshold: Detection threshold (relative magnitude, 0.0-1.0). 
                      Default 0.3 provides good balance between sensitivity and false positives.

        Returns:
            str: Detected digit ('0'-'9', '*', '#', 'A'-'D') or None
        """
        if len(samples) < self.samples_per_frame:
            return None

        # Check if signal has sufficient energy (reject silence/very weak signals)
        max_val = max(abs(s) for s in samples)
        if max_val < 0.01:  # Reject very weak signals before normalization
            return None

        # Normalize samples (max_val guaranteed to be >= 0.01 from check above)
        normalized = [s / (max_val or 1.0) for s in samples[:self.samples_per_frame]]

        # Detect low and high frequency components
        low_magnitudes = {freq: self.goertzel(normalized, freq) for freq in DTMF_LOW_FREQS}
        high_magnitudes = {freq: self.goertzel(normalized, freq) for freq in DTMF_HIGH_FREQS}

        # Find strongest frequencies
        low_freq = max(low_magnitudes, key=low_magnitudes.get)
        high_freq = max(high_magnitudes, key=high_magnitudes.get)
        
        low_mag = low_magnitudes[low_freq]
        high_mag = high_magnitudes[high_freq]

        # Check if both frequencies are strong enough
        # Also verify they are significantly stronger than other frequencies (noise rejection)
        if low_mag > threshold and high_mag > threshold:
            # Additional validation: check that detected frequencies are dominant
            # Require detected frequencies to be at least 2x stronger than the average of other frequencies
            other_low_mags = [m for f, m in low_magnitudes.items() if f != low_freq]
            other_high_mags = [m for f, m in high_magnitudes.items() if f != high_freq]
            
            avg_other_low = sum(other_low_mags) / len(other_low_mags) if other_low_mags else 0
            avg_other_high = sum(other_high_mags) / len(other_high_mags) if other_high_mags else 0
            
            # Require the detected frequencies to be significantly stronger than noise
            # Use 2.0 ratio for better noise rejection
            if low_mag > avg_other_low * 2.0 and high_mag > avg_other_high * 2.0:
                # Find matching digit
                for digit, (low, high) in DTMF_FREQUENCIES.items():
                    if low == low_freq and high == high_freq:
                        self.logger.debug(f"Detected DTMF tone: {digit} (L:{low_freq}Hz={low_mag:.3f}, H:{high_freq}Hz={high_mag:.3f})")
                        return digit

        return None

    def detect(self, audio_bytes: bytes, threshold: float = 0.3) -> Optional[str]:
        """
        Detect DTMF tone from raw audio bytes (PCM 16-bit signed little-endian)
        
        This is a convenience wrapper that converts raw audio bytes to samples
        and calls detect_tone(). Useful for processing RTP audio packets.
        
        Args:
            audio_bytes: Raw audio data (PCM 16-bit signed little-endian)
            threshold: Detection threshold (0.0-1.0)
        
        Returns:
            str: Detected digit ('0'-'9', '*', '#', 'A'-'D') or None
        """
        import struct
        
        # Convert bytes to samples (16-bit signed PCM)
        # Each sample is 2 bytes (little-endian signed short)
        num_samples = len(audio_bytes) // 2
        
        if num_samples < self.samples_per_frame:
            return None
        
        # Unpack bytes to signed 16-bit integers, then normalize to [-1.0, 1.0]
        try:
            samples = []
            # Process complete 2-byte pairs only (ignore last byte if length is odd)
            for i in range(0, num_samples * 2, 2):
                # Read 2 bytes as signed 16-bit little-endian
                sample_int = struct.unpack('<h', audio_bytes[i:i+2])[0]
                # Normalize to [-1.0, 1.0]
                samples.append(sample_int / 32768.0)
            
            # Use existing detect_tone method with noise rejection
            return self.detect_tone(samples, threshold)
        except struct.error:
            # Invalid audio data
            return None

    def detect_sequence(self, samples: List[float], max_digits: int = 10) -> str:
        """
        Detect sequence of DTMF tones from longer audio sample

        Args:
            samples: Audio samples
            max_digits: Maximum number of digits to detect

        Returns:
            str: Detected digit sequence
        """
        digits = []
        last_digit = None
        last_digit_count = 0
        
        # Process audio in frames
        frame_size = self.samples_per_frame
        frame_step = frame_size // 2  # 50% overlap
        
        for i in range(0, len(samples) - frame_size, frame_step):
            frame = samples[i:i + frame_size]
            digit = self.detect_tone(frame)
            
            if digit:
                if digit == last_digit:
                    last_digit_count += 1
                else:
                    # New digit detected, require multiple consecutive detections
                    if last_digit and last_digit_count >= 2:
                        digits.append(last_digit)
                        if len(digits) >= max_digits:
                            break
                    last_digit = digit
                    last_digit_count = 1
            else:
                # Silence - finalize previous digit if detected enough times
                if last_digit and last_digit_count >= 2:
                    digits.append(last_digit)
                    if len(digits) >= max_digits:
                        break
                last_digit = None
                last_digit_count = 0
        
        # Add final digit if present
        if last_digit and last_digit_count >= 2 and len(digits) < max_digits:
            digits.append(last_digit)
        
        result = ''.join(digits)
        if result:
            self.logger.info(f"Detected DTMF sequence: {result}")
        return result


class DTMFGenerator:
    """Generate DTMF tones for testing"""

    def __init__(self, sample_rate: int = 8000):
        """
        Initialize DTMF generator

        Args:
            sample_rate: Audio sample rate (Hz)
        """
        self.sample_rate = sample_rate
        self.logger = get_logger()

    def generate_tone(self, digit: str, duration_ms: int = 100) -> List[float]:
        """
        Generate DTMF tone for a digit

        Args:
            digit: Digit to generate ('0'-'9', '*', '#')
            duration_ms: Tone duration in milliseconds

        Returns:
            list: Audio samples
        """
        if digit not in DTMF_FREQUENCIES:
            self.logger.warning(f"Invalid DTMF digit: {digit}")
            return []

        low_freq, high_freq = DTMF_FREQUENCIES[digit]
        num_samples = int(self.sample_rate * duration_ms / 1000)
        
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            # Generate sum of two sine waves
            sample = (math.sin(2 * math.pi * low_freq * t) +
                     math.sin(2 * math.pi * high_freq * t)) / 2
            samples.append(sample)
        
        self.logger.debug(f"Generated DTMF tone for '{digit}': {num_samples} samples")
        return samples

    def generate_sequence(self, digits: str, tone_ms: int = 100, gap_ms: int = 50) -> List[float]:
        """
        Generate sequence of DTMF tones

        Args:
            digits: Digit sequence
            tone_ms: Duration of each tone
            gap_ms: Gap between tones

        Returns:
            list: Audio samples
        """
        samples = []
        gap_samples = [0.0] * int(self.sample_rate * gap_ms / 1000)
        
        for digit in digits:
            tone_samples = self.generate_tone(digit, tone_ms)
            samples.extend(tone_samples)
            samples.extend(gap_samples)
        
        self.logger.info(f"Generated DTMF sequence: {digits} ({len(samples)} samples)")
        return samples
