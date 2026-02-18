"""
Security Runtime Monitor
Continuously monitors and enforces security compliance during PBX operation
"""

import threading
import time
from datetime import UTC, datetime

from pbx.utils.encryption import CRYPTO_AVAILABLE, get_encryption
from pbx.utils.logger import get_logger


class SecurityMonitor:
    """
    Runtime security monitoring and enforcement system
    Ensures FIPS compliance and security features remain active during operation
    """

    def __init__(self, config: dict | None = None, webhook_system: object = None) -> None:
        """
        Initialize security monitor

        Args:
            config: PBX configuration object
            webhook_system: Optional webhook system for security alerts
        """
        self.logger = get_logger()
        self.config = config or {}
        self.webhook_system = webhook_system
        self.running = False
        self.monitor_thread = None

        # Monitoring configuration
        self.check_interval = self._get_config(
            "security.monitoring.check_interval", 300
        )  # 5 minutes
        self.enforce_fips = self._get_config("security.enforce_fips", True)
        self.fips_mode = self._get_config("security.fips_mode", True)

        # Security state tracking
        self.last_check_time = None
        self.compliance_status = {
            "fips_compliant": False,
            "crypto_available": False,
            "password_policy_active": False,
            "rate_limiting_active": False,
            "audit_logging_active": False,
            "threat_detection_active": False,
        }
        self.security_violations = []

    def _get_config(self, key: str, default: object = None) -> object:
        """
        Get config value supporting both dot notation and nested dicts

        Args:
            key: Config key (e.g., 'security.fips_mode')
            default: Default value if not found

        Returns:
            Config value or default
        """
        # Try dot notation first (Config object)
        if hasattr(self.config, "get") and "." in key:
            value = self.config.get(key, None)
            if value is not None:
                return value

        # Try nested dict navigation
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value if value is not None else default

    def start(self) -> None:
        """Start security monitoring"""
        if self.running:
            self.logger.warning("Security monitor already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, name="SecurityMonitor", daemon=True
        )
        self.monitor_thread.start()
        self.logger.info("Security runtime monitor started")

        # The monitor thread will perform the first security check
        # No need to call it here to avoid duplicate logs at startup

    def stop(self) -> None:
        """Stop security monitoring"""
        if not self.running:
            return

        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Security runtime monitor stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.running:
            try:
                # Perform periodic security check
                self.perform_security_check()

                # Sleep until next check
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Security monitor error: {e}")
                time.sleep(60)  # Shorter retry on error

    def perform_security_check(self) -> dict:
        """
        Perform comprehensive security compliance check

        Returns:
            Dictionary with check results
        """
        self.last_check_time = datetime.now(UTC)
        results = {
            "timestamp": self.last_check_time.isoformat(),
            "checks": {},
            "violations": [],
            "overall_status": "COMPLIANT",
        }

        # Check FIPS compliance
        fips_check = self._check_fips_compliance()
        results["checks"]["fips"] = fips_check
        self.compliance_status["fips_compliant"] = fips_check["status"] == "PASS"
        self.compliance_status["crypto_available"] = CRYPTO_AVAILABLE

        # Check password policy enforcement
        password_check = self._check_password_policy()
        results["checks"]["password_policy"] = password_check
        self.compliance_status["password_policy_active"] = password_check["status"] == "PASS"

        # Check rate limiting
        rate_limit_check = self._check_rate_limiting()
        results["checks"]["rate_limiting"] = rate_limit_check
        self.compliance_status["rate_limiting_active"] = rate_limit_check["status"] == "PASS"

        # Check audit logging
        audit_check = self._check_audit_logging()
        results["checks"]["audit_logging"] = audit_check
        self.compliance_status["audit_logging_active"] = audit_check["status"] == "PASS"

        # Check threat detection
        threat_check = self._check_threat_detection()
        results["checks"]["threat_detection"] = threat_check
        self.compliance_status["threat_detection_active"] = threat_check["status"] == "PASS"

        # Collect violations
        for check_name, check_result in results["checks"].items():
            if check_result["status"] == "FAIL":
                violation = {
                    "timestamp": self.last_check_time.isoformat(),
                    "check": check_name,
                    "severity": check_result.get("severity", "MEDIUM"),
                    "message": check_result.get("message", "Check failed"),
                }
                results["violations"].append(violation)
                self.security_violations.append(violation)

        # Determine overall status
        if results["violations"]:
            # Check for critical violations
            critical = any(v["severity"] == "CRITICAL" for v in results["violations"])
            if critical:
                results["overall_status"] = "CRITICAL"
            else:
                results["overall_status"] = "WARNING"

        # Log results
        if results["overall_status"] == "COMPLIANT":
            self.logger.info("Security compliance check: PASSED")
        elif results["overall_status"] == "WARNING":
            self.logger.warning(
                f"Security compliance check: WARNINGS ({len(results['violations'])} issues)"
            )
            for violation in results["violations"]:
                self.logger.warning(f"  - {violation['check']}: {violation['message']}")
            # Send webhook alert for warnings
            self._send_security_alert(results, "WARNING")
        else:
            self.logger.error(
                f"Security compliance check: CRITICAL ({len(results['violations'])} issues)"
            )
            for violation in results["violations"]:
                self.logger.error(f"  - {violation['check']}: {violation['message']}")
            # Send webhook alert for critical issues
            self._send_security_alert(results, "CRITICAL")

        return results

    def _send_security_alert(self, results: dict, severity: str) -> None:
        """
        Send security alert via webhook

        Args:
            results: Security check results
            severity: Alert severity (WARNING or CRITICAL)
        """
        if not self.webhook_system:
            return

        try:
            # Create security alert event
            event_data = {
                "event": "security.compliance_alert",
                "severity": severity,
                "timestamp": results["timestamp"],
                "overall_status": results["overall_status"],
                "violations_count": len(results["violations"]),
                "violations": results["violations"],
                "checks": {
                    check_name: {
                        "status": check_data.get("status"),
                        "message": check_data.get("message", ""),
                    }
                    for check_name, check_data in results["checks"].items()
                },
            }

            # Send webhook
            self.webhook_system.trigger("security.compliance_alert", event_data)
            self.logger.info(f"Security alert sent via webhook (severity: {severity})")
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to send security alert via webhook: {e}")

    def _check_fips_compliance(self) -> dict[str, object]:
        """Check FIPS 140-2 compliance status"""
        result = {
            "name": "FIPS 140-2 Compliance",
            "status": "PASS",
            "severity": "CRITICAL",
            "details": {},
        }

        # Check if FIPS mode is enabled in config
        if not self.fips_mode:
            result["status"] = "FAIL"
            result["message"] = "FIPS mode is disabled in configuration"
            result["details"]["fips_mode"] = False
            return result

        # Check if cryptography library is available
        if not CRYPTO_AVAILABLE:
            result["status"] = "FAIL"
            result["message"] = "Cryptography library not available - FIPS algorithms unavailable"
            result["details"]["crypto_available"] = False

            # This is critical if enforcement is enabled
            if self.enforce_fips:
                result["severity"] = "CRITICAL"
            return result

        # Try to initialize encryption with FIPS mode
        try:
            enc = get_encryption(fips_mode=True, enforce_fips=self.enforce_fips)

            # Test basic encryption operations
            test_password = "TestSecurityCheck123!"
            hash_val, salt = enc.hash_password(test_password)
            verified = enc.verify_password(test_password, hash_val, salt)

            if not verified:
                result["status"] = "FAIL"
                result["message"] = "FIPS encryption verification failed"
                result["details"]["encryption_test"] = False
                return result

            result["details"]["crypto_available"] = True
            result["details"]["encryption_test"] = True
            result["details"]["fips_mode"] = True
            result["message"] = "FIPS 140-2 compliance verified"

        except (KeyError, TypeError, ValueError) as e:
            result["status"] = "FAIL"
            result["message"] = f"FIPS compliance check failed: {e!s}"
            result["details"]["error"] = str(e)

        return result

    def _check_password_policy(self) -> dict[str, object]:
        """Check password policy enforcement"""
        result = {"name": "Password Policy", "status": "PASS", "severity": "HIGH", "details": {}}

        # Check minimum password length
        min_length = self._get_config("security.password.min_length", 0)
        if min_length < 12:
            result["status"] = "FAIL"
            result["message"] = f"Password minimum length too short: {min_length} (should be >= 12)"
            result["details"]["min_length"] = min_length
            return result

        # Check complexity requirements
        require_uppercase = self._get_config("security.password.require_uppercase", False)
        require_lowercase = self._get_config("security.password.require_lowercase", False)
        require_digit = self._get_config("security.password.require_digit", False)
        require_special = self._get_config("security.password.require_special", False)

        if not all([require_uppercase, require_lowercase, require_digit, require_special]):
            result["status"] = "FAIL"
            result["message"] = "Password complexity requirements not fully enabled"
            result["details"] = {
                "uppercase": require_uppercase,
                "lowercase": require_lowercase,
                "digit": require_digit,
                "special": require_special,
            }
            return result

        result["details"] = {"min_length": min_length, "complexity_enabled": True}
        result["message"] = "Password policy properly configured"

        return result

    def _check_rate_limiting(self) -> dict[str, object]:
        """Check rate limiting configuration"""
        result = {"name": "Rate Limiting", "status": "PASS", "severity": "HIGH", "details": {}}

        max_attempts = self._get_config("security.rate_limit.max_attempts", 0)
        window_seconds = self._get_config("security.rate_limit.window_seconds", 0)
        lockout_duration = self._get_config("security.rate_limit.lockout_duration", 0)

        if max_attempts == 0 or window_seconds == 0:
            result["status"] = "FAIL"
            result["message"] = "Rate limiting not configured"
            result["details"] = {"max_attempts": max_attempts, "window_seconds": window_seconds}
            return result

        result["details"] = {
            "max_attempts": max_attempts,
            "window_seconds": window_seconds,
            "lockout_duration": lockout_duration,
        }
        result["message"] = "Rate limiting properly configured"

        return result

    def _check_audit_logging(self) -> dict[str, object]:
        """Check security audit logging"""
        result = {
            "name": "Security Audit Logging",
            "status": "PASS",
            "severity": "MEDIUM",
            "details": {},
        }

        audit_enabled = self._get_config("security.audit.enabled", False)
        log_to_database = self._get_config("security.audit.log_to_database", False)

        if not audit_enabled:
            result["status"] = "FAIL"
            result["message"] = "Security audit logging is disabled"
            result["details"]["enabled"] = False
            return result

        result["details"] = {"enabled": audit_enabled, "log_to_database": log_to_database}
        result["message"] = "Security audit logging enabled"

        return result

    def _check_threat_detection(self) -> dict[str, object]:
        """Check threat detection system"""
        result = {"name": "Threat Detection", "status": "PASS", "severity": "MEDIUM", "details": {}}

        # Threat detection is optional but recommended
        # Default to False if not configured to avoid false positives
        threat_enabled = self._get_config("security.threat_detection.enabled", False)

        result["details"] = {"enabled": threat_enabled}

        if threat_enabled:
            result["message"] = "Threat detection system enabled"
        else:
            result["status"] = "WARNING"
            result["message"] = "Threat detection system disabled (optional but recommended)"

        return result

    def get_compliance_status(self) -> dict[str, object]:
        """
        Get current compliance status

        Returns:
            Dictionary with compliance information
        """
        return {
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "status": self.compliance_status.copy(),
            "recent_violations": self.security_violations[-10:] if self.security_violations else [],
        }

    def enforce_security_requirements(self) -> bool:
        """
        Enforce critical security requirements
        Returns False if system should shut down due to violations

        Returns:
            bool: True if system can continue, False if critical violations found
        """
        # Perform check
        results = self.perform_security_check()

        # If FIPS enforcement is enabled and FIPS check failed, system must stop
        if self.enforce_fips and not self.compliance_status["fips_compliant"]:
            self.logger.error("CRITICAL: FIPS compliance enforcement failed")
            self.logger.error("System cannot continue with enforce_fips=true")
            return False

        # Check for other critical violations
        critical_violations = [
            v for v in results.get("violations", []) if v.get("severity") == "CRITICAL"
        ]

        if critical_violations:
            self.logger.error(
                f"CRITICAL: {len(critical_violations)} critical security violations detected"
            )
            for violation in critical_violations:
                self.logger.error(f"  - {violation['check']}: {violation['message']}")

            # Check if critical violations should block system operation
            block_on_critical = self._get_config("security.block_on_critical_violations", False)
            if block_on_critical:
                self.logger.error(
                    "System cannot continue: block_on_critical_violations is enabled "
                    f"and {len(critical_violations)} critical violation(s) were found"
                )
                return False

            self.logger.warning(
                "Allowing system to continue despite critical violations "
                "(set security.block_on_critical_violations=true to enforce)"
            )
            return True

        return True


def get_security_monitor(
    config: dict | None = None, webhook_system: object = None
) -> SecurityMonitor:
    """Get security monitor instance"""
    return SecurityMonitor(config, webhook_system)
