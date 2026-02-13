"""
Test suite for Auto Attendant functionality
"""

import os
import shutil
import sys
import tempfile
import unittest
from typing import Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.features.auto_attendant import AAState, AutoAttendant, DestinationType


class TestAutoAttendant(unittest.TestCase):
    """Test Auto Attendant functionality"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        # Create a temporary directory for audio files
        self.test_audio_dir = tempfile.mkdtemp()

        # Create a mock config
        self.config_data = {
            "auto_attendant": {
                "enabled": True,
                "extension": "0",
                "timeout": 10,
                "max_retries": 3,
                "operator_extension": "1001",
                "audio_path": self.test_audio_dir,
                "menu_options": [
                    {"digit": "1", "destination": "8001", "description": "Sales Queue"},
                    {"digit": "2", "destination": "8002", "description": "Support Queue"},
                    {"digit": "3", "destination": "1003", "description": "Accounting"},
                    {"digit": "0", "destination": "1001", "description": "Operator"},
                ],
            }
        }

        # Create mock config object
        self.config = MockConfig(self.config_data)

        # Initialize auto attendant
        self.aa = AutoAttendant(self.config)

    def tearDown(self) -> None:
        """Clean up test fixtures"""
        # Remove temporary audio directory
        if os.path.exists(self.test_audio_dir):
            shutil.rmtree(self.test_audio_dir)

    def test_initialization(self) -> None:
        """Test auto attendant initialization"""
        self.assertTrue(self.aa.is_enabled())
        self.assertEqual(self.aa.get_extension(), "0")
        self.assertEqual(len(self.aa.menu_options), 4)

    def test_start_session(self) -> None:
        """Test starting an auto attendant session"""
        result = self.aa.start_session("test-call-123", "1001")

        self.assertEqual(result["action"], "play")
        self.assertIsNotNone(result.get("session"))
        self.assertEqual(result["session"]["state"], AAState.MAIN_MENU)
        self.assertEqual(result["session"]["from_extension"], "1001")

    def test_menu_selection_sales(self) -> None:
        """Test selecting sales queue option"""
        # Start session
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # Simulate DTMF '1' for sales
        result = self.aa.handle_dtmf(session, "1")

        self.assertEqual(result["action"], "transfer")
        self.assertEqual(result["destination"], "8001")
        self.assertEqual(result["session"]["state"], AAState.TRANSFERRING)

    def test_menu_selection_support(self) -> None:
        """Test selecting support queue option"""
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # Simulate DTMF '2' for support
        result = self.aa.handle_dtmf(session, "2")

        self.assertEqual(result["action"], "transfer")
        self.assertEqual(result["destination"], "8002")

    def test_menu_selection_operator(self) -> None:
        """Test selecting operator option"""
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # Simulate DTMF '0' for operator
        result = self.aa.handle_dtmf(session, "0")

        self.assertEqual(result["action"], "transfer")
        self.assertEqual(result["destination"], "1001")

    def test_invalid_input(self) -> None:
        """Test handling invalid menu option"""
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # Simulate invalid DTMF '9'
        result = self.aa.handle_dtmf(session, "9")

        self.assertEqual(result["action"], "play")
        self.assertEqual(result["session"]["state"], AAState.INVALID)
        self.assertEqual(result["session"]["retry_count"], 1)

    def test_max_retries_invalid(self) -> None:
        """Test maximum retries for invalid input"""
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # The auto attendant cycles through states:
        # MAIN_MENU + invalid digit -> INVALID state (retry_count++)
        # INVALID + any digit -> MAIN_MENU (no retry increment, just replay menu)
        # So it takes 2 DTMF presses per retry cycle
        #
        # Cycle 1: invalid '9' -> INVALID (retry=1), then '9' -> MAIN_MENU
        # Cycle 2: invalid '9' -> INVALID (retry=2), then '9' -> MAIN_MENU
        # Cycle 3: invalid '9' -> TRANSFER (retry=3, meets threshold)

        attempts = 0
        while attempts < 10:  # Safety limit
            result = self.aa.handle_dtmf(session, "9")
            session = result["session"]
            attempts += 1
            if result["action"] == "transfer":
                break

        # Should transfer to operator after max retries
        self.assertEqual(result["action"], "transfer")
        self.assertEqual(result["destination"], "1001")
        self.assertEqual(result.get("reason"), "invalid_input")
        # Should happen on 5th keypress (3 invalid + 2 menu replays)
        self.assertLessEqual(attempts, 6)

    def test_timeout_handling(self) -> None:
        """Test timeout handling"""
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # Simulate timeout
        result = self.aa.handle_timeout(session)

        self.assertEqual(result["action"], "play")
        self.assertEqual(result["session"]["retry_count"], 1)

    def test_max_timeouts(self) -> None:
        """Test maximum timeouts"""
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        # Simulate multiple timeouts
        for i in range(self.aa.max_retries):
            result = self.aa.handle_timeout(session)
            session = result["session"]

        # Should transfer to operator after max timeouts
        self.assertEqual(result["action"], "transfer")
        self.assertEqual(result["destination"], "1001")
        self.assertEqual(result.get("reason"), "timeout")

    def test_get_menu_text(self) -> None:
        """Test getting menu text description"""
        menu_text = self.aa.get_menu_text()

        self.assertIn("Auto Attendant Menu", menu_text)
        self.assertIn("Press 1", menu_text)
        self.assertIn("Sales Queue", menu_text)
        self.assertIn("Press 2", menu_text)
        self.assertIn("Support Queue", menu_text)

    def test_end_session(self) -> None:
        """Test ending a session"""
        result = self.aa.start_session("test-call-123", "1001")
        session = result["session"]

        self.aa.end_session(session)

        self.assertEqual(session["state"], AAState.ENDED)


class MockConfig:
    """Mock configuration object for testing"""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split(".")
        value = self.data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default


class TestAudioPromptGeneration(unittest.TestCase):
    """Test audio prompt generation"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_generate_prompts(self) -> None:
        """Test generating audio prompt files"""
        from pbx.features.auto_attendant import generate_auto_attendant_prompts

        # Generate prompts in test directory
        generate_auto_attendant_prompts(self.test_dir)

        # Check that files were created
        expected_files = [
            "welcome.wav",
            "main_menu.wav",
            "invalid.wav",
            "timeout.wav",
            "transferring.wav",
        ]

        for filename in expected_files:
            file_path = os.path.join(self.test_dir, filename)
            self.assertTrue(os.path.exists(file_path), f"File {filename} should exist")

            # Check that file is not empty
            file_size = os.path.getsize(file_path)
            self.assertGreater(file_size, 0, f"File {filename} should not be empty")

            # Check WAV header (should start with 'RIFF')
            with open(file_path, "rb") as f:
                header = f.read(4)
                self.assertEqual(header, b"RIFF", f"File {filename} should be a valid WAV file")


def run_all_tests() -> bool:
    """Run all tests in this module"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    unittest.main()
