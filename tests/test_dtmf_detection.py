"""
Test suite for DTMF detection functionality
Tests that DTMF detector properly filters noise and only detects real tones
"""
import math
import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.utils.dtmf import DTMF_FREQUENCIES, DTMFDetector, DTMFGenerator


class TestDTMFDetection(unittest.TestCase):
    """Test DTMF tone detection"""

    def setUp(self):
        """Set up test fixtures"""
        self.detector = DTMFDetector(sample_rate=8000, samples_per_frame=205)
        self.generator = DTMFGenerator(sample_rate=8000)

    def test_detect_valid_tone_1(self):
        """Test detection of valid DTMF tone '1'"""
        # Generate a clean DTMF tone for '1'
        samples = self.generator.generate_tone('1', duration_ms=100)

        # Detector should recognize it
        digit = self.detector.detect_tone(samples)
        self.assertEqual(digit, '1')

    def test_detect_valid_tone_5(self):
        """Test detection of valid DTMF tone '5'"""
        samples = self.generator.generate_tone('5', duration_ms=100)
        digit = self.detector.detect_tone(samples)
        self.assertEqual(digit, '5')

    def test_detect_valid_tone_star(self):
        """Test detection of valid DTMF tone '*'"""
        samples = self.generator.generate_tone('*', duration_ms=100)
        digit = self.detector.detect_tone(samples)
        self.assertEqual(digit, '*')

    def test_detect_valid_tone_pound(self):
        """Test detection of valid DTMF tone '#'"""
        samples = self.generator.generate_tone('#', duration_ms=100)
        digit = self.detector.detect_tone(samples)
        self.assertEqual(digit, '#')

    def test_no_detection_on_silence(self):
        """Test that silence does not trigger false DTMF detection"""
        # Create silence (all zeros)
        samples = [0.0] * 205

        # Detector should NOT detect any tone
        digit = self.detector.detect_tone(samples)
        self.assertIsNone(digit, "Silence should not be detected as DTMF tone")

    def test_no_detection_on_white_noise(self):
        """Test that white noise does not trigger false DTMF detection"""
        import random

        # Create white noise (random samples between -0.1 and 0.1)
        samples = [random.uniform(-0.1, 0.1) for _ in range(205)]

        # Detector should NOT detect any tone
        digit = self.detector.detect_tone(samples)
        self.assertIsNone(
            digit, "White noise should not be detected as DTMF tone")

    def test_no_detection_on_single_frequency(self):
        """Test that a single frequency tone is not detected as DTMF"""
        # DTMF requires TWO frequencies (low + high)
        # Generate a single frequency tone at 697 Hz (DTMF low freq)
        samples = []
        for i in range(205):
            t = i / 8000
            sample = math.sin(2 * math.pi * 697 * t)
            samples.append(sample)

        # Detector should NOT detect a tone (needs both low and high freq)
        digit = self.detector.detect_tone(samples)
        self.assertIsNone(
            digit, "Single frequency should not be detected as DTMF tone")

    def test_no_detection_on_weak_tone(self):
        """Test that very weak tones are not detected"""
        # Generate a very weak DTMF tone (amplitude 0.005, below 0.01
        # threshold)
        low_freq, high_freq = DTMF_FREQUENCIES['1']
        samples = []
        for i in range(205):
            t = i / 8000
            sample = 0.005 * (math.sin(2 * math.pi * low_freq * t) +
                              math.sin(2 * math.pi * high_freq * t)) / 2
            samples.append(sample)

        # Detector should NOT detect such a weak tone (below 0.01 energy
        # threshold)
        digit = self.detector.detect_tone(samples)
        self.assertIsNone(
            digit, "Very weak tones (below energy threshold) should not be detected")

    def test_detect_sequence(self):
        """Test detection of a sequence of DTMF tones"""
        # Generate a sequence "123"
        samples = self.generator.generate_sequence(
            "123", tone_ms=100, gap_ms=50)

        # Detect the sequence
        sequence = self.detector.detect_sequence(samples)

        # Should detect the full sequence
        self.assertEqual(sequence, "123")

    def test_threshold_parameter(self):
        """Test that threshold parameter works correctly"""
        # Generate a medium-strength tone
        samples = self.generator.generate_tone('5', duration_ms=100)

        # With normal threshold (0.3), should detect
        digit = self.detector.detect_tone(samples, threshold=0.3)
        self.assertEqual(digit, '5')

        # With lower threshold (0.1), should still detect
        digit = self.detector.detect_tone(samples, threshold=0.1)
        self.assertEqual(digit, '5')

        # Note: Very high thresholds (>0.8) may not reject clean tones since
        # the Goertzel algorithm produces high magnitudes for matching
        # frequencies

    def test_noise_rejection_ratio(self):
        """Test that detector properly handles noisy signals"""
        # Create a signal with DTMF tone mixed with noise at other frequencies
        low_freq, high_freq = DTMF_FREQUENCIES['1']
        samples = []
        for i in range(205):
            t = i / 8000
            # Strong DTMF signal
            dtmf_signal = 0.5 * (math.sin(2 * math.pi * low_freq * t) +
                                 math.sin(2 * math.pi * high_freq * t)) / 2
            # Weaker noise at non-DTMF frequency
            noise = 0.15 * math.sin(2 * math.pi * 800 * t)
            samples.append(dtmf_signal + noise)

        # Detector should detect this (DTMF is dominant over noise)
        digit = self.detector.detect_tone(samples)
        self.assertEqual(
            digit,
            '1',
            "DTMF tone should be detected when dominant over noise")


class TestDTMFGenerator(unittest.TestCase):
    """Test DTMF tone generation"""

    def setUp(self):
        """Set up test fixtures"""
        self.generator = DTMFGenerator(sample_rate=8000)

    def test_generate_tone(self):
        """Test generating a single DTMF tone"""
        samples = self.generator.generate_tone('1', duration_ms=100)

        # Should generate approximately 800 samples (100ms at 8000 Hz)
        self.assertAlmostEqual(len(samples), 800, delta=10)

        # Samples should be in valid range [-1, 1]
        self.assertTrue(all(-1.0 <= s <= 1.0 for s in samples))

    def test_generate_invalid_digit(self):
        """Test generating tone for invalid digit"""
        samples = self.generator.generate_tone('X', duration_ms=100)

        # Should return empty list
        self.assertEqual(samples, [])

    def test_generate_sequence(self):
        """Test generating a sequence of tones"""
        samples = self.generator.generate_sequence(
            "123", tone_ms=100, gap_ms=50)

        # Should generate samples for 3 tones + 3 gaps
        # 3 * (100ms tone + 50ms gap) = 3 * 150ms = 450ms total
        # At 8000Hz: 450ms * 8 samples/ms = 3600 samples
        expected_samples = 3 * (800 + 400)  # 3 * (100ms tone + 50ms gap)
        self.assertAlmostEqual(len(samples), expected_samples, delta=50)


def run_all_tests():
    """Run all tests in this module"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    unittest.main()
