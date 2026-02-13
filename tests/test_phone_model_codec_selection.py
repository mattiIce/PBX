"""
Tests for phone model-specific codec selection
"""

import os
import sys
import unittest
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.core.pbx import PBXCore


class TestPhoneModelDetection(unittest.TestCase):
    """Test phone model detection from User-Agent"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        # Create a minimal test instance with just the needed method
        self.pbx = Mock(spec=PBXCore)
        # Copy the actual method from the class to our mock
        self.pbx._detect_phone_model = PBXCore._detect_phone_model.__get__(self.pbx)

    def test_detect_zip33g_uppercase(self) -> None:
        """Test detection of ZIP33G in uppercase"""
        user_agent = "Zultys ZIP33G 47.80.0.132"
        model = self.pbx._detect_phone_model(user_agent)
        self.assertEqual(model, "ZIP33G")

    def test_detect_zip33g_with_space(self) -> None:
        """Test detection of ZIP 33G with space"""
        user_agent = "Zultys ZIP 33G firmware 47.80"
        model = self.pbx._detect_phone_model(user_agent)
        self.assertEqual(model, "ZIP33G")

    def test_detect_zip37g_uppercase(self) -> None:
        """Test detection of ZIP37G in uppercase"""
        user_agent = "Zultys ZIP37G 47.85.0.140"
        model = self.pbx._detect_phone_model(user_agent)
        self.assertEqual(model, "ZIP37G")

    def test_detect_zip37g_with_space(self) -> None:
        """Test detection of ZIP 37G with space"""
        user_agent = "Zultys ZIP 37G firmware 47.85"
        model = self.pbx._detect_phone_model(user_agent)
        self.assertEqual(model, "ZIP37G")

    def test_detect_other_phone(self) -> None:
        """Test detection of non-Zultys phone"""
        user_agent = "Yealink SIP-T46S 66.85.0.5"
        model = self.pbx._detect_phone_model(user_agent)
        self.assertIsNone(model)

    def test_detect_none_user_agent(self) -> None:
        """Test detection with None user agent"""
        model = self.pbx._detect_phone_model(None)
        self.assertIsNone(model)

    def test_detect_empty_user_agent(self) -> None:
        """Test detection with empty user agent"""
        model = self.pbx._detect_phone_model("")
        self.assertIsNone(model)

    def test_detect_zip33g_case_insensitive(self) -> None:
        """Test detection is case-insensitive"""
        user_agent = "zultys zip33g firmware"
        model = self.pbx._detect_phone_model(user_agent)
        self.assertEqual(model, "ZIP33G")


class TestCodecSelection(unittest.TestCase):
    """Test codec selection based on phone model"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        # Create a minimal test instance with just the needed attributes and method
        self.pbx = Mock(spec=PBXCore)
        self.pbx.config = Mock()
        self.pbx.config.get.return_value = 101  # DTMF payload type
        self.pbx.logger = Mock()  # Mock logger
        # Copy the actual method from the class to our mock
        self.pbx._get_codecs_for_phone_model = PBXCore._get_codecs_for_phone_model.__get__(self.pbx)

    def test_zip37g_codecs(self) -> None:
        """Test that ZIP37G gets PCMU/PCMA codecs"""
        codecs = self.pbx._get_codecs_for_phone_model("ZIP37G")
        # Should contain PCMU (0), PCMA (8), and DTMF (101)
        self.assertIn("0", codecs)  # PCMU
        self.assertIn("8", codecs)  # PCMA
        self.assertIn("101", codecs)  # DTMF
        # Should NOT contain G722, G729, or G726
        self.assertNotIn("9", codecs)  # G722
        self.assertNotIn("18", codecs)  # G729
        self.assertNotIn("2", codecs)  # G726-32
        # Verify the exact codec list
        self.assertEqual(set(codecs), {"0", "8", "101"})

    def test_zip33g_codecs(self) -> None:
        """Test that ZIP33G gets G726/G729/G722 codecs"""
        codecs = self.pbx._get_codecs_for_phone_model("ZIP33G")
        # Should contain G726 (2), G729 (18), G722 (9)
        self.assertIn("2", codecs)  # G726-32
        self.assertIn("18", codecs)  # G729
        self.assertIn("9", codecs)  # G722
        self.assertIn("101", codecs)  # DTMF
        # Should also include G726 variants
        self.assertIn("114", codecs)  # G726-40
        self.assertIn("113", codecs)  # G726-24
        self.assertIn("112", codecs)  # G726-16
        # Should NOT contain PCMU/PCMA
        self.assertNotIn("0", codecs)  # PCMU
        self.assertNotIn("8", codecs)  # PCMA
        # Verify the exact codec list
        self.assertEqual(set(codecs), {"2", "18", "9", "114", "113", "112", "101"})

    def test_unknown_phone_uses_defaults(self) -> None:
        """Test that unknown phones use default codecs"""
        default_codecs = ["0", "8", "9", "101"]
        codecs = self.pbx._get_codecs_for_phone_model(None, default_codecs=default_codecs)
        self.assertEqual(codecs, default_codecs)

    def test_unknown_phone_no_defaults(self) -> None:
        """Test that unknown phones get standard codec list when no defaults"""
        codecs = self.pbx._get_codecs_for_phone_model(None)
        # Should get standard fallback list
        self.assertIn("0", codecs)  # PCMU
        self.assertIn("8", codecs)  # PCMA
        self.assertIn("9", codecs)  # G722
        self.assertIn("18", codecs)  # G729
        self.assertIn("2", codecs)  # G726-32
        self.assertIn("101", codecs)  # DTMF

    def test_custom_dtmf_payload(self) -> None:
        """Test that custom DTMF payload type is used"""
        self.pbx.config.get.return_value = 96  # Custom DTMF payload
        codecs = self.pbx._get_codecs_for_phone_model("ZIP37G")
        self.assertIn("96", codecs)
        self.assertNotIn("101", codecs)


if __name__ == "__main__":
    unittest.main()
