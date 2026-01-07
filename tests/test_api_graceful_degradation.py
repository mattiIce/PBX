"""
Test API endpoint graceful degradation when features are disabled.

Tests that endpoints return appropriate empty responses instead of errors
when features like paging, LCR, etc. are not enabled.
"""

import json
import os
import sys
import unittest
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pbx.api.rest_api import PBXAPIHandler


class TestAPIGracefulDegradation(unittest.TestCase):
    """Test that API endpoints handle missing features gracefully"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a minimal mock PBX core without optional features
        self.pbx_core = MagicMock()
        self.pbx_core.config = MagicMock()

        # Set up handler
        PBXAPIHandler.pbx_core = self.pbx_core
        
        # Create a minimal handler mock
        self.handler = MagicMock(spec=PBXAPIHandler)
        self.handler.pbx_core = self.pbx_core
        self.handler.headers = {}
        self.handler.path = "/"
        self.handler.wfile = BytesIO()
        self.handler.logger = MagicMock()
        
        # Track response
        self.response_data = None
        self.response_status = 200
        
    def _capture_json_response(self, data, status=200):
        """Helper to capture JSON response"""
        self.response_data = data
        self.response_status = status

    def test_paging_zones_when_disabled(self):
        """Test that /api/paging/zones returns empty array when paging is disabled"""
        # Configure pbx_core without paging system
        if hasattr(self.pbx_core, 'paging_system'):
            del self.pbx_core.paging_system

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        
        # Call the method
        PBXAPIHandler._handle_get_paging_zones(self.handler)

        # Should return empty zones, not error
        self.assertIsNotNone(self.response_data)
        self.assertIn("zones", self.response_data)
        self.assertEqual(self.response_data["zones"], [])
        self.assertEqual(self.response_status, 200)

    def test_paging_devices_when_disabled(self):
        """Test that /api/paging/devices returns empty array when paging is disabled"""
        # Configure pbx_core without paging system
        if hasattr(self.pbx_core, 'paging_system'):
            del self.pbx_core.paging_system

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        
        # Call the method
        PBXAPIHandler._handle_get_paging_devices(self.handler)

        # Should return empty devices, not error
        self.assertIsNotNone(self.response_data)
        self.assertIn("devices", self.response_data)
        self.assertEqual(self.response_data["devices"], [])
        self.assertEqual(self.response_status, 200)

    def test_active_pages_when_disabled(self):
        """Test that /api/paging/active returns empty array when paging is disabled"""
        # Configure pbx_core without paging system
        if hasattr(self.pbx_core, 'paging_system'):
            del self.pbx_core.paging_system

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        
        # Call the method
        PBXAPIHandler._handle_get_active_pages(self.handler)

        # Should return empty active_pages, not error
        self.assertIsNotNone(self.response_data)
        self.assertIn("active_pages", self.response_data)
        self.assertEqual(self.response_data["active_pages"], [])
        self.assertEqual(self.response_status, 200)

    def test_lcr_rates_when_disabled(self):
        """Test that /api/lcr/rates returns empty array when LCR is disabled"""
        # Configure pbx_core without LCR
        if hasattr(self.pbx_core, 'lcr'):
            del self.pbx_core.lcr

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        
        # Call the method
        PBXAPIHandler._handle_get_lcr_rates(self.handler)

        # Should return empty rates, not error
        self.assertIsNotNone(self.response_data)
        self.assertIn("rates", self.response_data)
        self.assertEqual(self.response_data["rates"], [])
        self.assertEqual(self.response_data["time_rates"], [])
        self.assertEqual(self.response_data["count"], 0)
        self.assertEqual(self.response_status, 200)

    def test_lcr_statistics_when_disabled(self):
        """Test that /api/lcr/statistics returns empty stats when LCR is disabled"""
        # Configure pbx_core without LCR
        if hasattr(self.pbx_core, 'lcr'):
            del self.pbx_core.lcr

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        
        # Call the method
        PBXAPIHandler._handle_get_lcr_statistics(self.handler)

        # Should return empty statistics, not error
        self.assertIsNotNone(self.response_data)
        self.assertIn("total_calls", self.response_data)
        self.assertEqual(self.response_data["total_calls"], 0)
        self.assertEqual(self.response_status, 200)

    def test_integration_activity_when_database_disabled(self):
        """Test that /api/framework/integrations/activity-log returns empty when DB is disabled"""
        # Configure pbx_core without database
        self.pbx_core.database = MagicMock()
        self.pbx_core.database.enabled = False

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        
        # Call the method
        PBXAPIHandler._handle_get_integration_activity(self.handler)

        # Should return empty activities, not error
        self.assertIsNotNone(self.response_data)
        self.assertIn("activities", self.response_data)
        self.assertEqual(self.response_data["activities"], [])
        self.assertEqual(self.response_status, 200)

    def test_dtmf_config_returns_defaults(self):
        """Test that /api/config/dtmf returns defaults when config is missing"""
        # Configure pbx_core with config that returns None
        self.pbx_core.config.get_dtmf_config.return_value = None

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        self.handler._require_admin = lambda: (True, {})
        
        # Call the method
        PBXAPIHandler._handle_get_dtmf_config(self.handler)

        # Should return default configuration, not error
        self.assertIsNotNone(self.response_data)
        self.assertIn("mode", self.response_data)
        self.assertIn("payload_type", self.response_data)
        self.assertEqual(self.response_data["mode"], "rfc2833")
        self.assertEqual(self.response_data["payload_type"], 101)
        self.assertEqual(self.response_status, 200)

    def test_dtmf_config_returns_defaults_when_unauthenticated(self):
        """Test that /api/config/dtmf returns defaults for unauthenticated users"""
        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        self.handler._require_admin = lambda: (False, None)  # Not authenticated
        
        # Call the method
        PBXAPIHandler._handle_get_dtmf_config(self.handler)

        # Should return default configuration, not 403 error
        self.assertIsNotNone(self.response_data)
        self.assertIn("mode", self.response_data)
        self.assertIn("payload_type", self.response_data)
        self.assertEqual(self.response_data["mode"], "rfc2833")
        self.assertEqual(self.response_data["payload_type"], 101)
        self.assertEqual(self.response_status, 200)

    def test_config_returns_empty_when_unauthenticated(self):
        """Test that /api/config returns empty config for unauthenticated users"""
        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler
        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        self.handler._require_admin = lambda: (False, None)  # Not authenticated
        
        # Call the method
        PBXAPIHandler._handle_get_config(self.handler)

        # Should return empty config structure, not 403 error
        self.assertIsNotNone(self.response_data)
        self.assertIn("smtp", self.response_data)
        self.assertIn("email", self.response_data)
        self.assertIn("integrations", self.response_data)
        self.assertEqual(self.response_data["smtp"]["host"], "")
        self.assertEqual(self.response_data["integrations"], {})
        self.assertEqual(self.response_status, 200)


if __name__ == "__main__":
    unittest.main()
