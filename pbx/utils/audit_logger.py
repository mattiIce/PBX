"""Audit logging for PBX admin actions.

Provides comprehensive audit trail for security and compliance.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    """Audit logger for administrative actions."""

    def __init__(self, log_file: Optional[str] = None):
        """Initialize audit logger.

        Args:
            log_file: Path to audit log file (default: logs/audit.log)
        """
        if log_file is None:
            base_dir = Path(__file__).parent.parent.parent
            log_dir = base_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = str(log_dir / "audit.log")

        self.log_file = log_file

        # Create dedicated audit logger
        self.logger = logging.getLogger("pbx.audit")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Don't propagate to root logger

        # Add file handler if not already present
        if not self.logger.handlers:
            # Ensure parent directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.FileHandler(log_file)
            handler.setLevel(logging.INFO)

            # Set restrictive permissions on the log file (owner read/write only)
            # This prevents unauthorized access to sensitive audit data
            if log_path.exists():
                os.chmod(log_file, 0o600)

            # JSON format for easy parsing
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", %(message)s}'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
            # Set permissions after handler is created (in case it creates the file)
            if log_path.exists():
                os.chmod(log_file, 0o600)

    def log_action(
        self,
        action: str,
        user: str,
        resource: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log an administrative action.

        Args:
            action: Action performed (e.g., "create", "update", "delete", "view")
            user: Username or identifier
            resource: Resource type (e.g., "extension", "config", "user")
            resource_id: Specific resource identifier
            details: Additional details about the action
            success: Whether action succeeded
            ip_address: Client IP address
            user_agent: Client user agent
        """
        log_entry = {
            "action": action,
            "user": user,
            "resource": resource,
            "success": success,
        }

        if resource_id:
            log_entry["resource_id"] = resource_id

        if ip_address:
            log_entry["ip_address"] = ip_address

        if user_agent:
            log_entry["user_agent"] = user_agent

        if details:
            # Sanitize sensitive data
            sanitized_details = self._sanitize_details(details)
            log_entry["details"] = sanitized_details

        # Convert to JSON string (without outer braces since formatter adds them)
        message = ", ".join(f'"{k}": {json.dumps(v)}' for k, v in log_entry.items())

        if success:
            self.logger.info(message)
        else:
            self.logger.warning(message)

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from details.

        Args:
            details: Details dictionary

        Returns:
            Sanitized details dictionary
        """
        sanitized = {}
        sensitive_keys = ["password", "secret", "token", "api_key", "private_key"]

        for key, value in details.items():
            key_lower = key.lower()

            # Mask sensitive values
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            # Keep other values
            else:
                sanitized[key] = value

        return sanitized

    # Convenience methods for common actions

    def log_login(self, user: str, success: bool, ip_address: str):
        """Log a login attempt."""
        self.log_action(
            action="login",
            user=user,
            resource="auth",
            success=success,
            ip_address=ip_address,
        )

    def log_logout(self, user: str, ip_address: str):
        """Log a logout."""
        self.log_action(
            action="logout", user=user, resource="auth", ip_address=ip_address
        )

    def log_extension_create(
        self, user: str, extension_number: str, details: Dict, ip_address: str
    ):
        """Log extension creation."""
        self.log_action(
            action="create",
            user=user,
            resource="extension",
            resource_id=extension_number,
            details=details,
            ip_address=ip_address,
        )

    def log_extension_update(
        self, user: str, extension_number: str, details: Dict, ip_address: str
    ):
        """Log extension update."""
        self.log_action(
            action="update",
            user=user,
            resource="extension",
            resource_id=extension_number,
            details=details,
            ip_address=ip_address,
        )

    def log_extension_delete(
        self, user: str, extension_number: str, ip_address: str
    ):
        """Log extension deletion."""
        self.log_action(
            action="delete",
            user=user,
            resource="extension",
            resource_id=extension_number,
            ip_address=ip_address,
        )

    def log_config_change(
        self, user: str, config_key: str, details: Dict, ip_address: str
    ):
        """Log configuration change."""
        self.log_action(
            action="update",
            user=user,
            resource="config",
            resource_id=config_key,
            details=details,
            ip_address=ip_address,
        )

    def log_password_change(self, user: str, target_user: str, ip_address: str):
        """Log password change."""
        self.log_action(
            action="password_change",
            user=user,
            resource="user",
            resource_id=target_user,
            ip_address=ip_address,
        )

    def log_permission_change(
        self, user: str, target_user: str, details: Dict, ip_address: str
    ):
        """Log permission change."""
        self.log_action(
            action="permission_change",
            user=user,
            resource="user",
            resource_id=target_user,
            details=details,
            ip_address=ip_address,
        )

    def log_security_event(
        self, event_type: str, user: str, details: Dict, ip_address: str
    ):
        """Log security event."""
        self.log_action(
            action=event_type,
            user=user,
            resource="security",
            details=details,
            success=False,  # Security events are typically failures
            ip_address=ip_address,
        )

    def log_data_export(
        self, user: str, export_type: str, details: Dict, ip_address: str
    ):
        """Log data export."""
        self.log_action(
            action="export",
            user=user,
            resource="data",
            resource_id=export_type,
            details=details,
            ip_address=ip_address,
        )

    def log_backup_operation(self, user: str, operation: str, details: Dict):
        """Log backup operation."""
        self.log_action(
            action=operation,
            user=user,
            resource="backup",
            details=details,
        )


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def configure_audit_logger(log_file: str):
    """Configure global audit logger.

    Args:
        log_file: Path to audit log file
    """
    global _audit_logger
    _audit_logger = AuditLogger(log_file=log_file)
