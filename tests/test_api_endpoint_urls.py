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
        assert dtmf_path_count >= 2

        # Check that the old incorrect path does NOT exist
        assert 'path == "/api/config/dtm"' not in self.rest_api_content

    def test_activity_log_endpoints(self) -> None:
        """Verify activity log endpoints use correct URL path"""
        # Check that the correct endpoint paths exist
        assert 'path == "/api/framework/integrations/activity-log"' in self.rest_api_content
        assert 'path == "/api/framework/integrations/activity-log/clear"' in self.rest_api_content

        # Check that the old incorrect path does NOT exist
        assert 'path == "/api/framework/integrations/activity"' not in self.rest_api_content

    def test_dtmf_handler_method_exists(self) -> None:
        """Verify DTMF handler methods are defined"""
        # Check that handler methods exist
        assert "def _handle_get_dtmf_config" in self.rest_api_content
        assert "def _handle_update_dtmf_config" in self.rest_api_content

    def test_activity_log_handler_methods_exist(self) -> None:
        """Verify activity log handler methods are defined"""
        # Check that handler methods exist
        assert "def _handle_get_integration_activity" in self.rest_api_content
        assert "def _handle_clear_integration_activity" in self.rest_api_content
