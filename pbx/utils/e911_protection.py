"""
E911 Protection Module
Prevents emergency (911) calls from being tested or accidentally placed
during development and testing scenarios.
"""

import os
import re

from pbx.utils.logger import get_logger


class E911Protection:
    """
    Provides protection mechanisms to prevent E911 calls during testing.

    This class ensures that emergency 911 calls are never placed during:
    - Unit testing
    - Integration testing
    - Development environments
    - Any scenario where TEST_MODE or similar flags are set
    """

    # Patterns that match E911/emergency numbers
    E911_PATTERNS = [
        r"^911$",  # Standard 911
        r"^[0-9]*911$",  # Enhanced 911 with numeric prefix
        r"^\*911$",  # Asterisk prefix (e.g., *911)
    ]

    def __init__(self, config=None):
        """
        Initialize E911 protection

        Args:
            config: Configuration object (optional)
        """
        self.logger = get_logger()
        self.config = config
        self._test_mode = self._detect_test_mode()

        if self._test_mode:
            self.logger.warning(
                "E911 Protection: TEST MODE DETECTED - All emergency calls will be blocked"
            )

    def _detect_test_mode(self):
        """
        Detect if running in test mode

        Returns:
            True if in test mode
        """
        # Check environment variables
        test_env_vars = [
            "PYTEST_CURRENT_TEST",  # pytest sets this
            "TEST_MODE",
            "TESTING",
            "PBX_TEST_MODE",
        ]

        for var in test_env_vars:
            if os.environ.get(var):
                return True

        # Check if test config is being used
        if self.config:
            config_file = getattr(self.config, "config_file", "")
            if "test" in config_file.lower():
                return True

        return False

    def is_e911_number(self, number):
        """
        Check if a number is an E911/emergency number

        Args:
            number: Phone number to check

        Returns:
            True if the number matches E911 patterns
        """
        if not number:
            return False

        # Convert to string and strip whitespace
        number_str = str(number).strip()

        # Check against all E911 patterns
        return any(re.match(pattern, number_str) for pattern in self.E911_PATTERNS)

    def block_if_e911(self, number, context=""):
        """
        Block call if number is E911 and in test mode

        Args:
            number: Phone number to check
            context: Context string for logging (e.g., "outbound call")

        Returns:
            True if call should be blocked, False otherwise
        """
        if not self.is_e911_number(number):
            return False

        # Always block in test mode
        if self._test_mode:
            msg = f"E911 Protection: BLOCKED emergency call to {number}"
            if context:
                msg += f" (context: {context})"
            self.logger.error(msg)
            return True

        # Log warning even in production mode
        msg = f"E911 Protection: Emergency call detected to {number}"
        if context:
            msg += f" (context: {context})"
        self.logger.warning(msg)

        return False

    def is_test_mode(self):
        """
        Check if currently in test mode

        Returns:
            True if in test mode
        """
        return self._test_mode
