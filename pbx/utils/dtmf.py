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
            k = int(0.5 + (samples_per_frame * freq / sample_rate))
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
            q0 = coeff * q1 - q2 + sample
            q2 = q1
            q1 = q0
        
        # Calculate magnitude
        magnitude = math.sqrt(q1 * q1 + q2 * q2 - q1 * q2 * coeff)
        return magnitude

    def detect_tone(self, samples: List[float], threshold: float = 0.01) -> Optional[str]:
        """
        Detect DTMF tone from audio samples

        Args:
            samples: Audio samples (should be samples_per_frame length)
            threshold: Detection threshold (relative to average magnitude)

        Returns:
            str: Detected digit ('0'-'9', '*', '#', 'A'-'D') or None
        """
        if len(samples) < self.samples_per_frame:
            return None

        # Normalize samples
        max_val = max(abs(s) for s in samples) or 1.0
        normalized = [s / max_val for s in samples[:self.samples_per_frame]]

        # Detect low and high frequency components
        low_magnitudes = {freq: self.goertzel(normalized, freq) for freq in DTMF_LOW_FREQS}
        high_magnitudes = {freq: self.goertzel(normalized, freq) for freq in DTMF_HIGH_FREQS}

        # Find strongest frequencies
        low_freq = max(low_magnitudes, key=low_magnitudes.get)
        high_freq = max(high_magnitudes, key=high_magnitudes.get)
        
        low_mag = low_magnitudes[low_freq]
        high_mag = high_magnitudes[high_freq]

        # Check if both frequencies are strong enough
        if low_mag > threshold and high_mag > threshold:
            # Find matching digit
            for digit, (low, high) in DTMF_FREQUENCIES.items():
                if low == low_freq and high == high_freq:
                    self.logger.debug(f"Detected DTMF tone: {digit} (L:{low_freq}Hz={low_mag:.3f}, H:{high_freq}Hz={high_mag:.3f})")
                    return digit

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
