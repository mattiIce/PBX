"""
Tests for phone model-specific codec selection
"""

from unittest.mock import Mock

from pbx.core.pbx import PBXCore


class TestPhoneModelDetection:
    """Test phone model detection from User-Agent"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        # Create a minimal test instance with just the needed method
        self.pbx = Mock(spec=PBXCore)
        # Copy the actual method from the class to our mock
        self.pbx._detect_phone_model = PBXCore._detect_phone_model.__get__(self.pbx)

    def test_detect_zip33g_uppercase(self) -> None:
        """Test detection of ZIP33G in uppercase"""
        user_agent = "Zultys ZIP33G 47.80.0.132"
        model = self.pbx._detect_phone_model(user_agent)
        assert model == "ZIP33G"

    def test_detect_zip33g_with_space(self) -> None:
        """Test detection of ZIP 33G with space"""
        user_agent = "Zultys ZIP 33G firmware 47.80"
        model = self.pbx._detect_phone_model(user_agent)
        assert model == "ZIP33G"

    def test_detect_zip37g_uppercase(self) -> None:
        """Test detection of ZIP37G in uppercase"""
        user_agent = "Zultys ZIP37G 47.85.0.140"
        model = self.pbx._detect_phone_model(user_agent)
        assert model == "ZIP37G"

    def test_detect_zip37g_with_space(self) -> None:
        """Test detection of ZIP 37G with space"""
        user_agent = "Zultys ZIP 37G firmware 47.85"
        model = self.pbx._detect_phone_model(user_agent)
        assert model == "ZIP37G"

    def test_detect_other_phone(self) -> None:
        """Test detection of non-Zultys phone"""
        user_agent = "Yealink SIP-T46S 66.85.0.5"
        model = self.pbx._detect_phone_model(user_agent)
        assert model is None

    def test_detect_none_user_agent(self) -> None:
        """Test detection with None user agent"""
        model = self.pbx._detect_phone_model(None)
        assert model is None

    def test_detect_empty_user_agent(self) -> None:
        """Test detection with empty user agent"""
        model = self.pbx._detect_phone_model("")
        assert model is None

    def test_detect_zip33g_case_insensitive(self) -> None:
        """Test detection is case-insensitive"""
        user_agent = "zultys zip33g firmware"
        model = self.pbx._detect_phone_model(user_agent)
        assert model == "ZIP33G"


class TestCodecSelection:
    """Test codec selection based on phone model"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        # Create a minimal test instance with just the needed attributes and method
        self.pbx = Mock(spec=PBXCore)
        self.pbx.config = Mock()
        self.pbx.config.get.return_value = 101  # DTMF payload type
        self.pbx.logger = Mock()  # Mock logger
        # Copy the actual method from the class to our mock
        self.pbx._get_codecs_for_phone_model = PBXCore._get_codecs_for_phone_model.__get__(self.pbx)

    def test_zip37g_codecs(self) -> None:
        """Test that ZIP37G gets full codec set matching provisioning template"""
        codecs = self.pbx._get_codecs_for_phone_model("ZIP37G")
        # Should contain PCMU (0), PCMA (8), G722 (9), G729 (18), G726-32 (2), and DTMF (101)
        # per the zultys_zip37g provisioning template
        assert "0" in codecs  # PCMU
        assert "8" in codecs  # PCMA
        assert "9" in codecs  # G722
        assert "18" in codecs  # G729
        assert "2" in codecs  # G726-32
        assert "101" in codecs  # DTMF
        # Verify the exact codec list
        assert set(codecs) == {"0", "8", "9", "18", "2", "101"}

    def test_zip33g_codecs(self) -> None:
        """Test that ZIP33G gets full codec set matching provisioning template"""
        codecs = self.pbx._get_codecs_for_phone_model("ZIP33G")
        # Should contain PCMU (0), PCMA (8), G722 (9), G729 (18), G726-32 (2), and DTMF (101)
        # per the zultys_zip33g provisioning template
        assert "0" in codecs  # PCMU
        assert "8" in codecs  # PCMA
        assert "9" in codecs  # G722
        assert "18" in codecs  # G729
        assert "2" in codecs  # G726-32
        assert "101" in codecs  # DTMF
        # Verify the exact codec list
        assert set(codecs) == {"0", "8", "9", "18", "2", "101"}

    def test_unknown_phone_uses_defaults(self) -> None:
        """Test that unknown phones use default codecs"""
        default_codecs = ["0", "8", "9", "101"]
        codecs = self.pbx._get_codecs_for_phone_model(None, default_codecs=default_codecs)
        assert codecs == default_codecs

    def test_unknown_phone_no_defaults(self) -> None:
        """Test that unknown phones get standard codec list when no defaults"""
        codecs = self.pbx._get_codecs_for_phone_model(None)
        # Should get standard fallback list
        assert "0" in codecs  # PCMU
        assert "8" in codecs  # PCMA
        assert "9" in codecs  # G722
        assert "18" in codecs  # G729
        assert "2" in codecs  # G726-32
        assert "101" in codecs  # DTMF

    def test_custom_dtmf_payload(self) -> None:
        """Test that custom DTMF payload type is used"""
        self.pbx.config.get.return_value = 96  # Custom DTMF payload
        codecs = self.pbx._get_codecs_for_phone_model("ZIP37G")
        assert "96" in codecs
        assert "101" not in codecs
