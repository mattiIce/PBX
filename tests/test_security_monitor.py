#!/usr/bin/env python3
"""
Tests for security runtime monitor
Verifies continuous security compliance monitoring
"""

import time

from pbx.utils.config import Config
from pbx.utils.security_monitor import SecurityMonitor, get_security_monitor


def test_security_monitor_initialization() -> None:
    """Test security monitor initialization"""

    # Create monitor with FIPS enabled
    config = {
        "security": {
            "fips_mode": True,
            "enforce_fips": True,
            "password": {
                "min_length": 12,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_digit": True,
                "require_special": True,
            },
            "rate_limit": {"max_attempts": 5, "window_seconds": 300, "lockout_duration": 900},
            "audit": {"enabled": True, "log_to_database": True},
            "threat_detection": {"enabled": True},
        }
    }

    monitor = SecurityMonitor(config)
    assert monitor is not None, "Monitor should be created"
    assert monitor.fips_mode is True, "FIPS mode should be enabled"
    assert monitor.enforce_fips is True, "FIPS enforcement should be enabled"


def test_fips_compliance_check() -> None:
    """Test FIPS compliance checking"""

    config = {"security": {"fips_mode": True, "enforce_fips": True}}

    monitor = SecurityMonitor(config)
    result = monitor._check_fips_compliance()

    assert result is not None, "Check should return result"
    assert "status" in result, "Result should have status"
    assert "name" in result, "Result should have name"
    assert result["name"] == "FIPS 140-2 Compliance", "Check name should be correct"

    # Check based on crypto library availability
    from pbx.utils.encryption import CRYPTO_AVAILABLE

    if CRYPTO_AVAILABLE:
        assert result["status"] == "PASS", "FIPS check should pass with crypto library"
    else:
        assert result["status"] == "FAIL", "FIPS check should fail without crypto library"


def test_password_policy_check() -> None:
    """Test password policy checking"""

    # Test with proper policy
    config = {
        "security": {
            "password": {
                "min_length": 12,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_digit": True,
                "require_special": True,
            }
        }
    }

    monitor = SecurityMonitor(config)
    result = monitor._check_password_policy()

    assert result["status"] == "PASS", "Password policy check should pass"
    assert result["details"]["min_length"] == 12, "Min length should be 12"

    # Test with weak policy
    weak_config = {"security": {"password": {"min_length": 6, "require_uppercase": False}}}

    weak_monitor = SecurityMonitor(weak_config)
    weak_result = weak_monitor._check_password_policy()

    assert weak_result["status"] == "FAIL", "Weak password policy should fail"


def test_rate_limiting_check() -> None:
    """Test rate limiting check"""

    config = {
        "security": {
            "rate_limit": {"max_attempts": 5, "window_seconds": 300, "lockout_duration": 900}
        }
    }

    monitor = SecurityMonitor(config)
    result = monitor._check_rate_limiting()

    assert result["status"] == "PASS", "Rate limiting check should pass"
    assert result["details"]["max_attempts"] == 5, "Max attempts should be 5"


def test_audit_logging_check() -> None:
    """Test audit logging check"""

    config = {"security": {"audit": {"enabled": True, "log_to_database": True}}}

    monitor = SecurityMonitor(config)
    result = monitor._check_audit_logging()

    assert result["status"] == "PASS", "Audit logging check should pass"
    assert result["details"]["enabled"] is True, "Audit logging should be enabled"


def test_threat_detection_check() -> None:
    """Test threat detection check"""

    config = {"security": {"threat_detection": {"enabled": True}}}

    monitor = SecurityMonitor(config)
    result = monitor._check_threat_detection()

    assert result["status"] == "PASS", "Threat detection check should pass"


def test_comprehensive_security_check() -> None:
    """Test comprehensive security check"""

    # Load actual config
    config = Config("config.yml")

    monitor = SecurityMonitor(config)
    results = monitor.perform_security_check()

    assert results is not None, "Check should return results"
    assert "timestamp" in results, "Results should have timestamp"
    assert "checks" in results, "Results should have checks"
    assert "violations" in results, "Results should have violations"
    assert "overall_status" in results, "Results should have overall status"

    # Check that all expected checks were performed
    expected_checks = [
        "fips",
        "password_policy",
        "rate_limiting",
        "audit_logging",
        "threat_detection",
    ]
    for check in expected_checks:
        assert check in results["checks"], f"Check '{check}' should be present"

    # Only log summary status, never the full results which may contain sensitive data.


def test_compliance_status() -> None:
    """Test compliance status tracking"""

    config = Config("config.yml")
    monitor = SecurityMonitor(config)

    # Perform check to update status
    monitor.perform_security_check()

    # Get compliance status
    status = monitor.get_compliance_status()

    assert status is not None, "Status should be returned"
    assert "last_check" in status, "Status should have last_check"
    assert "status" in status, "Status should have status dict"
    assert "recent_violations" in status, "Status should have recent_violations"

    # Check status fields
    status_fields = [
        "fips_compliant",
        "crypto_available",
        "password_policy_active",
        "rate_limiting_active",
        "audit_logging_active",
        "threat_detection_active",
    ]
    for field in status_fields:
        assert field in status["status"], f"Status should have '{field}' field"


def test_security_enforcement() -> None:
    """Test security enforcement"""

    config = Config("config.yml")
    monitor = SecurityMonitor(config)

    # Test enforcement
    can_continue = monitor.enforce_security_requirements()

    # Should return True unless critical FIPS failure with enforcement
    assert isinstance(can_continue, bool), "Enforcement should return boolean"

    if not can_continue:
        pass


def test_monitor_lifecycle() -> None:
    """Test monitor start/stop lifecycle"""

    config = Config("config.yml")
    monitor = SecurityMonitor(config)

    # Start monitor
    monitor.start()
    assert monitor.running, "Monitor should be running"
    assert monitor.monitor_thread is not None, "Monitor thread should exist"

    # Let it run briefly (2 seconds to ensure thread is active)
    time.sleep(2)

    # Stop monitor
    monitor.stop()
    assert not monitor.running, "Monitor should be stopped"


def test_get_security_monitor() -> None:
    """Test factory function"""

    config = Config("config.yml")
    monitor = get_security_monitor(config)

    assert monitor is not None, "Factory should return monitor"
    assert isinstance(monitor, SecurityMonitor), "Should return SecurityMonitor instance"
