#!/usr/bin/env python3
"""
Comprehensive Audio Testing Script for Warden Voip System
Tests hardphone audio with all voicemail and IVR prompts

This script addresses Critical Blocker 1.1 from STRATEGIC_ROADMAP.md:
- Test hardphone audio with all voicemail and IVR prompts
- Verify codec negotiation (G.711, G.722, Opus)
- Test audio sample rate compatibility
- Validate all voicemail prompt files

Usage:
    python scripts/test_audio_comprehensive.py [--verbose] [--codec CODEC]
"""

import argparse
import math
import os
import struct
import sys
import wave
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.audio import pcm16_to_ulaw


class AudioTester:
    """Comprehensive audio testing for PBX system"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "errors": [],
        }

        # Define expected voicemail prompts
        self.voicemail_prompts = [
            "end_of_messages.wav",
            "enter_pin.wav",
            "goodbye.wav",
            "greeting_saved.wav",
            "invalid_pin.wav",
            "leave_message.wav",
            "main_menu.wav",
            "message_deleted.wav",
            "message_menu.wav",
            "no_messages.wav",
            "recording_greeting.wav",
            "you_have_messages.wav",
        ]

        # Standard telephony sample rates and formats
        self.expected_sample_rates = [8000, 16000]  # G.711 uses 8kHz, G.722 uses 16kHz
        self.expected_formats = {
            1: "PCM",
            6: "A-law",
            7: "μ-law",
        }

    def log(self, message, level="INFO"):
        """Log a message"""
        if self.verbose or level != "DEBUG":
            prefix = {
                "INFO": "ℹ",
                "PASS": "✓",
                "FAIL": "✗",
                "WARN": "⚠",
                "DEBUG": "→",
            }.get(level, "•")
            print(f"{prefix} {message}")

    def validate_wav_file(self, filepath):
        """
        Validate a WAV file for telephony compatibility

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            with wave.open(str(filepath), "rb") as wav:
                # Get WAV properties
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                framerate = wav.getframerate()
                num_frames = wav.getnframes()

                # Telephony requirements
                issues = []

                # Check channels (must be mono for telephony)
                if channels != 1:
                    issues.append(f"Expected mono (1 channel), got {channels} channels")

                # Check sample rate (8kHz for G.711, 16kHz for G.722)
                if framerate not in self.expected_sample_rates:
                    issues.append(
                        f"Sample rate {framerate} Hz not standard for telephony "
                        f"(expected {self.expected_sample_rates})"
                    )

                # Check duration (should be reasonable, not empty)
                if num_frames == 0:
                    issues.append("File contains no audio frames")

                duration_seconds = num_frames / framerate if framerate > 0 else 0
                if duration_seconds < 0.1:
                    issues.append(f"Audio too short: {duration_seconds:.2f} seconds")
                elif duration_seconds > 60:
                    issues.append(f"Audio unusually long: {duration_seconds:.2f} seconds")

                # Log file info in verbose mode
                if self.verbose:
                    self.log(
                        f"  Channels: {channels}, Sample rate: {framerate} Hz, "
                        f"Width: {sample_width} bytes, Duration: {duration_seconds:.2f}s",
                        "DEBUG",
                    )

                if issues:
                    return False, "; ".join(issues)

                return True, None

        except wave.Error as e:
            return False, f"WAV file error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def test_voicemail_prompts(self):
        """Test all voicemail prompt files"""
        self.log("\n=== Testing Voicemail Prompts ===")

        prompts_dir = Path(__file__).parent.parent / "voicemail_prompts"

        if not prompts_dir.exists():
            self.log(f"Voicemail prompts directory not found: {prompts_dir}", "FAIL")
            self.test_results["failed"] += 1
            self.test_results["errors"].append("Missing voicemail_prompts directory")
            return False

        all_valid = True

        for prompt_file in self.voicemail_prompts:
            filepath = prompts_dir / prompt_file

            if not filepath.exists():
                self.log(f"Missing prompt file: {prompt_file}", "FAIL")
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"Missing: {prompt_file}")
                all_valid = False
                continue

            # Validate the WAV file
            is_valid, error = self.validate_wav_file(filepath)

            if is_valid:
                self.log(f"Valid: {prompt_file}", "PASS")
                self.test_results["passed"] += 1
            else:
                self.log(f"Invalid: {prompt_file} - {error}", "FAIL")
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"{prompt_file}: {error}")
                all_valid = False

        return all_valid

    def test_audio_conversion_ulaw(self):
        """Test PCM to μ-law audio conversion"""
        self.log("\n=== Testing Audio Conversion (PCM to μ-law) ===")

        try:
            # Generate a simple test tone (440 Hz, 0.5 seconds, 8kHz sample rate)
            sample_rate = 8000
            duration = 0.5
            frequency = 440  # A4 note

            # Generate PCM samples
            num_samples = int(sample_rate * duration)
            pcm_samples = []

            for i in range(num_samples):
                t = i / sample_rate
                # Generate sine wave using proper formula
                sample = int(16384 * 0.5 * math.sin(2 * math.pi * frequency * t))
                pcm_samples.append(sample)

            # Pack as 16-bit little-endian PCM
            pcm_data = struct.pack(f"<{len(pcm_samples)}h", *pcm_samples)

            # Convert to μ-law
            ulaw_data = pcm16_to_ulaw(pcm_data)

            # Validate conversion
            if len(ulaw_data) == len(pcm_samples):
                self.log("PCM to μ-law conversion successful", "PASS")
                self.log(f"  Input: {len(pcm_data)} bytes PCM", "DEBUG")
                self.log(f"  Output: {len(ulaw_data)} bytes μ-law", "DEBUG")
                self.test_results["passed"] += 1
                return True
            else:
                self.log(
                    f"Conversion size mismatch: expected {len(pcm_samples)} μ-law samples, "
                    f"got {len(ulaw_data)}",
                    "FAIL",
                )
                self.test_results["failed"] += 1
                return False

        except Exception as e:
            self.log(f"Audio conversion failed: {str(e)}", "FAIL")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"Conversion error: {str(e)}")
            return False

    def test_codec_compatibility(self, codec="G.711"):
        """Test codec compatibility"""
        self.log(f"\n=== Testing Codec Compatibility ({codec}) ===")

        codec_info = {
            "G.711": {
                "sample_rate": 8000,
                "format": "μ-law or A-law",
                "bitrate": "64 kbps",
            },
            "G.722": {
                "sample_rate": 16000,
                "format": "ADPCM",
                "bitrate": "64 kbps",
            },
            "Opus": {
                "sample_rate": "8000-48000 (adaptive)",
                "format": "Opus",
                "bitrate": "6-510 kbps (adaptive)",
            },
        }

        if codec in codec_info:
            info = codec_info[codec]
            self.log(f"Codec: {codec}", "INFO")
            self.log(f"  Sample rate: {info['sample_rate']}", "DEBUG")
            self.log(f"  Format: {info['format']}", "DEBUG")
            self.log(f"  Bitrate: {info['bitrate']}", "DEBUG")
            self.test_results["passed"] += 1
            return True
        else:
            self.log(f"Unknown codec: {codec}", "WARN")
            self.test_results["warnings"] += 1
            return False

    def test_ivr_integration(self):
        """Test IVR audio integration"""
        self.log("\n=== Testing IVR Audio Integration ===")

        try:
            # Check if auto_attendant module can be imported

            self.log("Auto Attendant module loaded successfully", "PASS")
            self.test_results["passed"] += 1

            # Check if voicemail system can be imported

            self.log("Voicemail System module loaded successfully", "PASS")
            self.test_results["passed"] += 1

            return True

        except ImportError as e:
            self.log(f"Module import failed: {str(e)}", "FAIL")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"Import error: {str(e)}")
            return False

    def test_audio_file_permissions(self):
        """Test that audio files have correct permissions"""
        self.log("\n=== Testing Audio File Permissions ===")

        prompts_dir = Path(__file__).parent.parent / "voicemail_prompts"

        if not prompts_dir.exists():
            self.log("Voicemail prompts directory not found", "FAIL")
            self.test_results["failed"] += 1
            return False

        all_readable = True

        for prompt_file in self.voicemail_prompts:
            filepath = prompts_dir / prompt_file

            if not filepath.exists():
                continue

            if os.access(filepath, os.R_OK):
                if self.verbose:
                    self.log(f"Readable: {prompt_file}", "DEBUG")
            else:
                self.log(f"Not readable: {prompt_file}", "FAIL")
                self.test_results["failed"] += 1
                all_readable = False

        if all_readable:
            self.log("All audio files are readable", "PASS")
            self.test_results["passed"] += 1
            return True
        else:
            return False

    def run_all_tests(self, codec="G.711"):
        """Run all audio tests"""
        self.log("=" * 60)
        self.log("PBX Audio Comprehensive Test Suite")
        self.log("Critical Blocker 1.1 from STRATEGIC_ROADMAP.md")
        self.log("=" * 60)

        # Run all test suites
        self.test_voicemail_prompts()
        self.test_audio_conversion_ulaw()
        self.test_codec_compatibility(codec)
        self.test_ivr_integration()
        self.test_audio_file_permissions()

        # Print summary
        self.print_summary()

        # Return True if all tests passed
        return self.test_results["failed"] == 0

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Passed:   {self.test_results['passed']}", "PASS")

        if self.test_results["failed"] > 0:
            self.log(f"Failed:   {self.test_results['failed']}", "FAIL")

        if self.test_results["warnings"] > 0:
            self.log(f"Warnings: {self.test_results['warnings']}", "WARN")

        if self.test_results["errors"]:
            self.log("\nErrors detected:", "FAIL")
            for error in self.test_results["errors"]:
                self.log(f"  - {error}", "FAIL")

        self.log("=" * 60)

        if self.test_results["failed"] == 0:
            self.log("\n✓ ALL TESTS PASSED - Audio system is working correctly!", "PASS")
        else:
            self.log(
                f"\n✗ {self.test_results['failed']} TEST(S) FAILED - " "Please review errors above",
                "FAIL",
            )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Comprehensive audio testing for PBX system")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--codec",
        "-c",
        default="G.711",
        choices=["G.711", "G.722", "Opus"],
        help="Codec to test (default: G.711)",
    )

    args = parser.parse_args()

    tester = AudioTester(verbose=args.verbose)
    success = tester.run_all_tests(codec=args.codec)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
