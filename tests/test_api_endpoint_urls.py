"""
Test API Endpoint URL Correctness
Tests that the REST API endpoints match the URLs expected by the admin UI.
"""

import os


class TestAPIEndpointURLs:
    """Test that API endpoint URLs are correctly defined"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test class by reading the REST API file once"""
        # Get the path to the rest_api.py file relative to this test file
        rest_api_path = os.path.join(os.path.dirname(__file__), "..", "pbx", "api", "rest_api.py")
        with open(rest_api_path, "r") as f:
            cls.rest_api_content = f.read()

    def test_dtmf_config_endpoints(self) -> None:
        """Verify DTMF config endpoints use correct URL path"""
        # Check that the correct endpoint paths exist for both GET and PUT/POST
        dtmf_path = 'path == "/api/config/dtmf"'
        dtmf_path_count = self.rest_api_content.count(dtmf_path)
        self.assertGreaterEqual(
            dtmf_path_count,
            2,
            "DTMF config path should be defined for both GET and PUT/POST endpoints",
        )

        # Check that the old incorrect path does NOT exist
        self.assertNotIn(
            'path == "/api/config/dtm"',
            self.rest_api_content,
            "Old incorrect DTMF endpoint should not exist",
        )

    def test_activity_log_endpoints(self) -> None:
        """Verify activity log endpoints use correct URL path"""
        # Check that the correct endpoint paths exist
        self.assertIn(
            'path == "/api/framework/integrations/activity-log"',
            self.rest_api_content,
            "GET endpoint for activity log",
        )
        self.assertIn(
            'path == "/api/framework/integrations/activity-log/clear"',
            self.rest_api_content,
            "POST endpoint for clearing activity log",
        )

        # Check that the old incorrect path does NOT exist
        self.assertNotIn(
            'path == "/api/framework/integrations/activity"',
            self.rest_api_content,
            "Old incorrect activity log endpoint should not exist",
        )

    def test_dtmf_handler_method_exists(self) -> None:
        """Verify DTMF handler methods are defined"""
        # Check that handler methods exist
        assert "def _handle_get_dtmf_config" in self.rest_api_content
        self.assertIn(
            "def _handle_update_dtmf_config", self.rest_api_content, "Update DTMF handler"
        )

    def test_activity_log_handler_methods_exist(self) -> None:
        """Verify activity log handler methods are defined"""
        # Check that handler methods exist
        self.assertIn(
            "def _handle_get_integration_activity",
            self.rest_api_content,
            "GET activity log handler",
        )
        self.assertIn(
            "def _handle_clear_integration_activity",
            self.rest_api_content,
            "Clear activity log handler",
        )
