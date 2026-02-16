"""
Test API endpoint graceful degradation when features are disabled.

Tests that endpoints return appropriate empty responses instead of errors
when features like paging, LCR, etc. are not enabled.
"""

import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, Mock, patch

from pbx.api.rest_api import PBXAPIHandler


class TestAPIGracefulDegradation:
    """Test that API endpoints handle missing features gracefully"""

    def setup_method(self) -> None:
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

    def _capture_json_response(self, data: Any, status: int = 200) -> None:
        """Helper to capture JSON response"""
        self.response_data = data
        self.response_status = status

    def _setup_handler_with_auth(self, is_admin: bool = True) -> type:
        """Helper to set up handler with authentication state"""
        from pbx.api.rest_api import PBXAPIHandler

        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)
        # Return consistent dict type for payload, with is_admin flag set accordingly
        payload = {"is_admin": is_admin} if is_admin else {}
        self.handler._require_admin = lambda: (is_admin, payload)
        return PBXAPIHandler

    def test_paging_zones_when_disabled(self) -> None:
        """Test that /api/paging/zones returns empty array when paging is disabled"""
        # Configure pbx_core without paging system
        if hasattr(self.pbx_core, "paging_system"):
            del self.pbx_core.paging_system

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler

        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)

        # Call the method
        PBXAPIHandler._handle_get_paging_zones(self.handler)

        # Should return empty zones, not error
        assert self.response_data is not None
        assert "zones" in self.response_data
        assert self.response_data["zones"] == []
        assert self.response_status == 200

    def test_paging_devices_when_disabled(self) -> None:
        """Test that /api/paging/devices returns empty array when paging is disabled"""
        # Configure pbx_core without paging system
        if hasattr(self.pbx_core, "paging_system"):
            del self.pbx_core.paging_system

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler

        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)

        # Call the method
        PBXAPIHandler._handle_get_paging_devices(self.handler)

        # Should return empty devices, not error
        assert self.response_data is not None
        assert "devices" in self.response_data
        assert self.response_data["devices"] == []
        assert self.response_status == 200

    def test_active_pages_when_disabled(self) -> None:
        """Test that /api/paging/active returns empty array when paging is disabled"""
        # Configure pbx_core without paging system
        if hasattr(self.pbx_core, "paging_system"):
            del self.pbx_core.paging_system

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler

        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)

        # Call the method
        PBXAPIHandler._handle_get_active_pages(self.handler)

        # Should return empty active_pages, not error
        assert self.response_data is not None
        assert "active_pages" in self.response_data
        assert self.response_data["active_pages"] == []
        assert self.response_status == 200

    def test_lcr_rates_when_disabled(self) -> None:
        """Test that /api/lcr/rates returns empty array when LCR is disabled"""
        # Configure pbx_core without LCR
        if hasattr(self.pbx_core, "lcr"):
            del self.pbx_core.lcr

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler

        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)

        # Call the method
        PBXAPIHandler._handle_get_lcr_rates(self.handler)

        # Should return empty rates, not error
        assert self.response_data is not None
        assert "rates" in self.response_data
        assert self.response_data["rates"] == []
        assert self.response_data["time_rates"] == []
        assert self.response_data["count"] == 0
        assert self.response_status == 200

    def test_lcr_statistics_when_disabled(self) -> None:
        """Test that /api/lcr/statistics returns empty stats when LCR is disabled"""
        # Configure pbx_core without LCR
        if hasattr(self.pbx_core, "lcr"):
            del self.pbx_core.lcr

        # Bind the real method to our mock handler
        from pbx.api.rest_api import PBXAPIHandler

        self.handler._send_json = lambda data, status=200: self._capture_json_response(data, status)

        # Call the method
        PBXAPIHandler._handle_get_lcr_statistics(self.handler)

        # Should return empty statistics, not error
        assert self.response_data is not None
        assert "total_calls" in self.response_data
        assert self.response_data["total_calls"] == 0
        assert self.response_status == 200

    def test_integration_activity_when_database_disabled(self) -> None:
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
        assert self.response_data is not None
        assert "activities" in self.response_data
        assert self.response_data["activities"] == []
        assert self.response_status == 200

    def test_dtmf_config_returns_defaults(self) -> None:
        """Test that /api/config/dtmf returns defaults when config is missing"""
        # Configure pbx_core with config that returns None
        self.pbx_core.config.get_dtmf_config.return_value = None

        # Set up handler with admin authentication
        PBXAPIHandler = self._setup_handler_with_auth(is_admin=True)

        # Call the method
        PBXAPIHandler._handle_get_dtmf_config(self.handler)

        # Should return default configuration, not error
        assert self.response_data is not None
        assert "mode" in self.response_data
        assert "payload_type" in self.response_data
        assert self.response_data["mode"] == "rfc2833"
        assert self.response_data["payload_type"] == 101
        assert self.response_status == 200

    def test_dtmf_config_returns_defaults_when_unauthenticated(self) -> None:
        """Test that /api/config/dtmf returns defaults for unauthenticated users"""
        # Set up handler without authentication
        PBXAPIHandler = self._setup_handler_with_auth(is_admin=False)

        # Call the method
        PBXAPIHandler._handle_get_dtmf_config(self.handler)

        # Should return default configuration, not 403 error
        assert self.response_data is not None
        assert "mode" in self.response_data
        assert "payload_type" in self.response_data
        assert self.response_data["mode"] == "rfc2833"
        assert self.response_data["payload_type"] == 101
        assert self.response_status == 200

    def test_config_returns_empty_when_unauthenticated(self) -> None:
        """Test that /api/config returns empty config for unauthenticated users"""
        # Set up handler without authentication
        PBXAPIHandler = self._setup_handler_with_auth(is_admin=False)

        # Call the method
        PBXAPIHandler._handle_get_config(self.handler)

        # Should return empty config structure, not 403 error
        assert self.response_data is not None
        assert "smtp" in self.response_data
        assert "email" in self.response_data
        assert "integrations" in self.response_data
        assert self.response_data["smtp"]["host"] == ""
        assert self.response_data["integrations"] == {}
        assert self.response_status == 200
