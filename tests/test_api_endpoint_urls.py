"""
Test API Endpoint URL Correctness
Tests that the REST API endpoints match the URLs expected by the admin UI.
"""

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestAPIEndpointURLs(unittest.TestCase):
    """Test that API endpoint URLs are correctly defined"""

    def test_dtmf_config_endpoints(self):
        """Verify DTMF config endpoints use correct URL path"""
        with open("pbx/api/rest_api.py", "r") as f:
            content = f.read()

        # Check that the correct endpoint paths exist
        self.assertIn('path == "/api/config/dtmf"', content, "GET endpoint for DTMF config")
        self.assertIn('path == "/api/config/dtmf"', content, "PUT/POST endpoint for DTMF config")

        # Check that the old incorrect path does NOT exist
        self.assertNotIn(
            'path == "/api/config/dtm"',
            content,
            "Old incorrect DTMF endpoint should not exist",
        )

    def test_activity_log_endpoints(self):
        """Verify activity log endpoints use correct URL path"""
        with open("pbx/api/rest_api.py", "r") as f:
            content = f.read()

        # Check that the correct endpoint paths exist
        self.assertIn(
            'path == "/api/framework/integrations/activity-log"',
            content,
            "GET endpoint for activity log",
        )
        self.assertIn(
            'path == "/api/framework/integrations/activity-log/clear"',
            content,
            "POST endpoint for clearing activity log",
        )

        # Check that the old incorrect path does NOT exist
        self.assertNotIn(
            'path == "/api/framework/integrations/activity"',
            content,
            "Old incorrect activity log endpoint should not exist",
        )

    def test_dtmf_handler_method_exists(self):
        """Verify DTMF handler methods are defined"""
        with open("pbx/api/rest_api.py", "r") as f:
            content = f.read()

        # Check that handler methods exist
        self.assertIn("def _handle_get_dtmf_config", content, "GET DTMF handler")
        self.assertIn("def _handle_update_dtmf_config", content, "Update DTMF handler")

    def test_activity_log_handler_methods_exist(self):
        """Verify activity log handler methods are defined"""
        with open("pbx/api/rest_api.py", "r") as f:
            content = f.read()

        # Check that handler methods exist
        self.assertIn(
            "def _handle_get_integration_activity", content, "GET activity log handler"
        )
        self.assertIn(
            "def _handle_clear_integration_activity", content, "Clear activity log handler"
        )


if __name__ == "__main__":
    unittest.main()
