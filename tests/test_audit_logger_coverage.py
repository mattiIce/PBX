"""Comprehensive tests for the AuditLogger module."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from pbx.utils.audit_logger import AuditLogger, configure_audit_logger, get_audit_logger


@pytest.mark.unit
class TestAuditLogger:
    """Tests for the AuditLogger class."""

    @patch("pbx.utils.audit_logger.logging.FileHandler")
    @patch("pbx.utils.audit_logger.Path")
    def test_init_default_log_file(
        self, mock_path_cls: MagicMock, mock_file_handler: MagicMock
    ) -> None:
        """Test initialization with default log file path."""
        mock_path_instance = MagicMock()
        mock_path_instance.parent = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        # We also need to handle the base_dir / "logs" path computation
        mock_path_cls.__truediv__ = MagicMock()

        with patch("pbx.utils.audit_logger.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = []
            mock_get_logger.return_value = mock_logger

            logger = AuditLogger()

            assert logger.log_file is not None
            mock_logger.setLevel.assert_called_once_with(logging.INFO)
            mock_logger.addHandler.assert_called_once()

    @patch("pbx.utils.audit_logger.logging.FileHandler")
    @patch("pbx.utils.audit_logger.Path")
    def test_init_custom_log_file(
        self, mock_path_cls: MagicMock, mock_file_handler: MagicMock
    ) -> None:
        """Test initialization with custom log file path."""
        mock_path_instance = MagicMock()
        mock_path_instance.parent = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        with patch("pbx.utils.audit_logger.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = []
            mock_get_logger.return_value = mock_logger

            logger = AuditLogger(log_file="/custom/audit.log")

            assert logger.log_file == "/custom/audit.log"
            mock_file_handler.assert_called_once_with("/custom/audit.log")

    @patch("pbx.utils.audit_logger.logging.FileHandler")
    @patch("pbx.utils.audit_logger.Path")
    def test_init_sets_permissions_on_existing_file(
        self, mock_path_cls: MagicMock, mock_file_handler: MagicMock
    ) -> None:
        """Test that permissions are set when log file already exists."""
        mock_path_instance = MagicMock()
        mock_path_instance.parent = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance

        with patch("pbx.utils.audit_logger.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = []
            mock_get_logger.return_value = mock_logger

            AuditLogger(log_file="/custom/audit.log")

            # chmod should be called (potentially twice - before and after handler creation)
            mock_path_instance.chmod.assert_called_with(0o600)

    @patch("pbx.utils.audit_logger.logging.FileHandler")
    @patch("pbx.utils.audit_logger.Path")
    def test_init_does_not_add_handler_if_already_present(
        self, mock_path_cls: MagicMock, mock_file_handler: MagicMock
    ) -> None:
        """Test that handler is not added if logger already has handlers."""
        mock_path_instance = MagicMock()
        mock_path_instance.parent = MagicMock()
        mock_path_cls.return_value = mock_path_instance

        with patch("pbx.utils.audit_logger.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = [MagicMock()]  # Already has a handler
            mock_get_logger.return_value = mock_logger

            AuditLogger(log_file="/custom/audit.log")

            mock_logger.addHandler.assert_not_called()
            mock_file_handler.assert_not_called()

    @patch("pbx.utils.audit_logger.logging.FileHandler")
    @patch("pbx.utils.audit_logger.Path")
    def test_propagate_disabled(
        self, mock_path_cls: MagicMock, mock_file_handler: MagicMock
    ) -> None:
        """Test that logger propagation is disabled."""
        mock_path_instance = MagicMock()
        mock_path_instance.parent = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        with patch("pbx.utils.audit_logger.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = []
            mock_get_logger.return_value = mock_logger

            AuditLogger(log_file="/custom/audit.log")

            assert mock_logger.propagate is False

    @patch("pbx.utils.audit_logger.logging.FileHandler")
    @patch("pbx.utils.audit_logger.Path")
    def _create_test_logger(
        self, mock_path_cls: MagicMock, mock_file_handler: MagicMock
    ) -> tuple[AuditLogger, MagicMock]:
        """Helper to create a test AuditLogger with mocked dependencies."""
        mock_path_instance = MagicMock()
        mock_path_instance.parent = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        with patch("pbx.utils.audit_logger.logging.getLogger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_logger_instance.handlers = []
            mock_get_logger.return_value = mock_logger_instance

            audit_logger = AuditLogger(log_file="/tmp/test_audit.log")
            return audit_logger, mock_logger_instance

    def test_log_action_basic(self) -> None:
        """Test basic log_action call."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_action(
            action="create",
            user="admin",
            resource="extension",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "create"' in call_args
        assert '"user": "admin"' in call_args
        assert '"resource": "extension"' in call_args

    def test_log_action_with_all_fields(self) -> None:
        """Test log_action with all optional fields."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_action(
            action="update",
            user="admin",
            resource="extension",
            resource_id="1001",
            details={"name": "New Name"},
            success=True,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"resource_id": "1001"' in call_args
        assert '"ip_address": "192.168.1.100"' in call_args
        assert '"user_agent": "Mozilla/5.0"' in call_args

    def test_log_action_failure_uses_warning(self) -> None:
        """Test that failed actions use warning level."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_action(
            action="login",
            user="admin",
            resource="auth",
            success=False,
        )

        mock_logger.warning.assert_called_once()
        mock_logger.info.assert_not_called()

    def test_log_action_success_uses_info(self) -> None:
        """Test that successful actions use info level."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_action(
            action="login",
            user="admin",
            resource="auth",
            success=True,
        )

        mock_logger.info.assert_called_once()
        mock_logger.warning.assert_not_called()

    def test_log_action_without_optional_fields(self) -> None:
        """Test log_action without resource_id, ip_address, user_agent, details."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_action(
            action="view",
            user="operator",
            resource="dashboard",
        )

        call_args = mock_logger.info.call_args[0][0]
        assert '"resource_id"' not in call_args
        assert '"ip_address"' not in call_args
        assert '"user_agent"' not in call_args
        assert '"details"' not in call_args

    def test_sanitize_details_password(self) -> None:
        """Test that password fields are redacted."""
        audit_logger, _ = self._create_test_logger()

        details = {"name": "John", "password": "secret123"}
        result = audit_logger._sanitize_details(details)

        assert result["name"] == "John"
        assert result["password"] == "***REDACTED***"

    def test_sanitize_details_api_key(self) -> None:
        """Test that api_key fields are redacted."""
        audit_logger, _ = self._create_test_logger()

        details = {"api_key": "abc123def456"}
        result = audit_logger._sanitize_details(details)

        assert result["api_key"] == "***REDACTED***"

    def test_sanitize_details_token(self) -> None:
        """Test that token fields are redacted."""
        audit_logger, _ = self._create_test_logger()

        details = {"access_token": "jwt-token-here"}
        result = audit_logger._sanitize_details(details)

        assert result["access_token"] == "***REDACTED***"

    def test_sanitize_details_secret(self) -> None:
        """Test that secret fields are redacted."""
        audit_logger, _ = self._create_test_logger()

        details = {"client_secret": "s3cr3t"}
        result = audit_logger._sanitize_details(details)

        assert result["client_secret"] == "***REDACTED***"

    def test_sanitize_details_private_key(self) -> None:
        """Test that private_key fields are redacted."""
        audit_logger, _ = self._create_test_logger()

        details = {"private_key": "-----BEGIN RSA PRIVATE KEY-----"}
        result = audit_logger._sanitize_details(details)

        assert result["private_key"] == "***REDACTED***"

    def test_sanitize_details_nested_dict(self) -> None:
        """Test that nested dictionaries are recursively sanitized."""
        audit_logger, _ = self._create_test_logger()

        details = {
            "config": {
                "name": "Test",
                "password": "nested_secret",
                "inner": {"api_key": "deep_key"},
            }
        }
        result = audit_logger._sanitize_details(details)

        assert result["config"]["name"] == "Test"
        assert result["config"]["password"] == "***REDACTED***"
        assert result["config"]["inner"]["api_key"] == "***REDACTED***"

    def test_sanitize_details_case_insensitive(self) -> None:
        """Test that sensitive key detection is case-insensitive."""
        audit_logger, _ = self._create_test_logger()

        details = {"Password": "secret", "API_KEY": "key123"}
        result = audit_logger._sanitize_details(details)

        assert result["Password"] == "***REDACTED***"
        assert result["API_KEY"] == "***REDACTED***"

    def test_sanitize_details_non_sensitive_preserved(self) -> None:
        """Test that non-sensitive values are preserved."""
        audit_logger, _ = self._create_test_logger()

        details = {"name": "Test", "count": 42, "enabled": True}
        result = audit_logger._sanitize_details(details)

        assert result == details

    def test_log_login_success(self) -> None:
        """Test log_login convenience method for successful login."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_login("admin", True, "10.0.0.1")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "login"' in call_args
        assert '"user": "admin"' in call_args
        assert '"resource": "auth"' in call_args
        assert '"ip_address": "10.0.0.1"' in call_args

    def test_log_login_failure(self) -> None:
        """Test log_login convenience method for failed login."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_login("hacker", False, "10.0.0.99")

        mock_logger.warning.assert_called_once()

    def test_log_logout(self) -> None:
        """Test log_logout convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_logout("admin", "10.0.0.1")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "logout"' in call_args
        assert '"resource": "auth"' in call_args

    def test_log_extension_create(self) -> None:
        """Test log_extension_create convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_extension_create(
            "admin", "1001", {"name": "Alice"}, "10.0.0.1"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "create"' in call_args
        assert '"resource": "extension"' in call_args
        assert '"resource_id": "1001"' in call_args

    def test_log_extension_update(self) -> None:
        """Test log_extension_update convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_extension_update(
            "admin", "1001", {"name": "Bob"}, "10.0.0.1"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "update"' in call_args

    def test_log_extension_delete(self) -> None:
        """Test log_extension_delete convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_extension_delete("admin", "1001", "10.0.0.1")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "delete"' in call_args
        assert '"resource": "extension"' in call_args

    def test_log_config_change(self) -> None:
        """Test log_config_change convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_config_change(
            "admin", "sip.port", {"old": 5060, "new": 5061}, "10.0.0.1"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "update"' in call_args
        assert '"resource": "config"' in call_args
        assert '"resource_id": "sip.port"' in call_args

    def test_log_password_change(self) -> None:
        """Test log_password_change convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_password_change("admin", "user1", "10.0.0.1")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "password_change"' in call_args
        assert '"resource": "user"' in call_args
        assert '"resource_id": "user1"' in call_args

    def test_log_permission_change(self) -> None:
        """Test log_permission_change convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_permission_change(
            "admin", "user1", {"role": "operator"}, "10.0.0.1"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "permission_change"' in call_args
        assert '"resource": "user"' in call_args

    def test_log_security_event(self) -> None:
        """Test log_security_event convenience method (always success=False)."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_security_event(
            "brute_force", "unknown", {"attempts": 100}, "10.0.0.99"
        )

        # Security events use success=False, so warning should be called
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert '"action": "brute_force"' in call_args
        assert '"resource": "security"' in call_args

    def test_log_data_export(self) -> None:
        """Test log_data_export convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_data_export(
            "admin", "call_records", {"format": "csv"}, "10.0.0.1"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "export"' in call_args
        assert '"resource": "data"' in call_args
        assert '"resource_id": "call_records"' in call_args

    def test_log_backup_operation(self) -> None:
        """Test log_backup_operation convenience method."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_backup_operation(
            "system", "create", {"size": "1.2GB"}
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '"action": "create"' in call_args
        assert '"resource": "backup"' in call_args

    def test_log_action_with_details_sanitization(self) -> None:
        """Test that details are sanitized when logging."""
        audit_logger, mock_logger = self._create_test_logger()

        audit_logger.log_action(
            action="update",
            user="admin",
            resource="user",
            details={"name": "Alice", "password": "secret123"},
        )

        call_args = mock_logger.info.call_args[0][0]
        assert "secret123" not in call_args
        assert "***REDACTED***" in call_args


@pytest.mark.unit
class TestGetAuditLogger:
    """Tests for the global audit logger functions."""

    @patch("pbx.utils.audit_logger.AuditLogger")
    def test_get_audit_logger_creates_singleton(self, mock_audit_cls: MagicMock) -> None:
        """Test that get_audit_logger creates a singleton instance."""
        import pbx.utils.audit_logger as audit_module

        original = audit_module._audit_logger
        audit_module._audit_logger = None
        try:
            mock_instance = MagicMock()
            mock_audit_cls.return_value = mock_instance

            result = get_audit_logger()

            assert result is mock_instance
            mock_audit_cls.assert_called_once()
        finally:
            audit_module._audit_logger = original

    @patch("pbx.utils.audit_logger.AuditLogger")
    def test_get_audit_logger_returns_existing(self, mock_audit_cls: MagicMock) -> None:
        """Test that get_audit_logger returns existing instance."""
        import pbx.utils.audit_logger as audit_module

        mock_existing = MagicMock()
        original = audit_module._audit_logger
        audit_module._audit_logger = mock_existing
        try:
            result = get_audit_logger()

            assert result is mock_existing
            mock_audit_cls.assert_not_called()
        finally:
            audit_module._audit_logger = original

    @patch("pbx.utils.audit_logger.AuditLogger")
    def test_configure_audit_logger(self, mock_audit_cls: MagicMock) -> None:
        """Test configure_audit_logger sets global instance with custom path."""
        import pbx.utils.audit_logger as audit_module

        original = audit_module._audit_logger
        try:
            mock_instance = MagicMock()
            mock_audit_cls.return_value = mock_instance

            configure_audit_logger("/custom/path/audit.log")

            mock_audit_cls.assert_called_once_with(log_file="/custom/path/audit.log")
            assert audit_module._audit_logger is mock_instance
        finally:
            audit_module._audit_logger = original

    @patch("pbx.utils.audit_logger.AuditLogger")
    def test_configure_replaces_existing(self, mock_audit_cls: MagicMock) -> None:
        """Test that configure_audit_logger replaces existing instance."""
        import pbx.utils.audit_logger as audit_module

        original = audit_module._audit_logger
        audit_module._audit_logger = MagicMock()
        try:
            new_instance = MagicMock()
            mock_audit_cls.return_value = new_instance

            configure_audit_logger("/new/audit.log")

            assert audit_module._audit_logger is new_instance
        finally:
            audit_module._audit_logger = original
