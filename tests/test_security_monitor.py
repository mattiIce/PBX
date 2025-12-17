#!/usr/bin/env python3
"""
Tests for security runtime monitor
Verifies continuous security compliance monitoring
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pbx.utils.security_monitor import SecurityMonitor, get_security_monitor
from pbx.utils.config import Config


def test_security_monitor_initialization():
    """Test security monitor initialization"""
    print("\nTesting security monitor initialization...")
    
    # Create monitor with FIPS enabled
    config = {
        'security': {
            'fips_mode': True,
            'enforce_fips': True,
            'password': {
                'min_length': 12,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_digit': True,
                'require_special': True
            },
            'rate_limit': {
                'max_attempts': 5,
                'window_seconds': 300,
                'lockout_duration': 900
            },
            'audit': {
                'enabled': True,
                'log_to_database': True
            },
            'threat_detection': {
                'enabled': True
            }
        }
    }
    
    monitor = SecurityMonitor(config)
    assert monitor is not None, "Monitor should be created"
    assert monitor.fips_mode == True, "FIPS mode should be enabled"
    assert monitor.enforce_fips == True, "FIPS enforcement should be enabled"
    
    print("  ✓ Security monitor initialization works")


def test_fips_compliance_check():
    """Test FIPS compliance checking"""
    print("\nTesting FIPS compliance check...")
    
    config = {
        'security': {
            'fips_mode': True,
            'enforce_fips': True
        }
    }
    
    monitor = SecurityMonitor(config)
    result = monitor._check_fips_compliance()
    
    assert result is not None, "Check should return result"
    assert 'status' in result, "Result should have status"
    assert 'name' in result, "Result should have name"
    assert result['name'] == 'FIPS 140-2 Compliance', "Check name should be correct"
    
    # Check based on crypto library availability
    from pbx.utils.encryption import CRYPTO_AVAILABLE
    if CRYPTO_AVAILABLE:
        assert result['status'] == 'PASS', "FIPS check should pass with crypto library"
        print("  ✓ FIPS compliance check works (cryptography available)")
    else:
        assert result['status'] == 'FAIL', "FIPS check should fail without crypto library"
        print("  ✓ FIPS compliance check works (cryptography unavailable)")


def test_password_policy_check():
    """Test password policy checking"""
    print("\nTesting password policy check...")
    
    # Test with proper policy
    config = {
        'security': {
            'password': {
                'min_length': 12,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_digit': True,
                'require_special': True
            }
        }
    }
    
    monitor = SecurityMonitor(config)
    result = monitor._check_password_policy()
    
    assert result['status'] == 'PASS', "Password policy check should pass"
    assert result['details']['min_length'] == 12, "Min length should be 12"
    print("  ✓ Password policy check works (proper policy)")
    
    # Test with weak policy
    weak_config = {
        'security': {
            'password': {
                'min_length': 6,
                'require_uppercase': False
            }
        }
    }
    
    weak_monitor = SecurityMonitor(weak_config)
    weak_result = weak_monitor._check_password_policy()
    
    assert weak_result['status'] == 'FAIL', "Weak password policy should fail"
    print("  ✓ Password policy check works (weak policy detected)")


def test_rate_limiting_check():
    """Test rate limiting check"""
    print("\nTesting rate limiting check...")
    
    config = {
        'security': {
            'rate_limit': {
                'max_attempts': 5,
                'window_seconds': 300,
                'lockout_duration': 900
            }
        }
    }
    
    monitor = SecurityMonitor(config)
    result = monitor._check_rate_limiting()
    
    assert result['status'] == 'PASS', "Rate limiting check should pass"
    assert result['details']['max_attempts'] == 5, "Max attempts should be 5"
    print("  ✓ Rate limiting check works")


def test_audit_logging_check():
    """Test audit logging check"""
    print("\nTesting audit logging check...")
    
    config = {
        'security': {
            'audit': {
                'enabled': True,
                'log_to_database': True
            }
        }
    }
    
    monitor = SecurityMonitor(config)
    result = monitor._check_audit_logging()
    
    assert result['status'] == 'PASS', "Audit logging check should pass"
    assert result['details']['enabled'] == True, "Audit logging should be enabled"
    print("  ✓ Audit logging check works")


def test_threat_detection_check():
    """Test threat detection check"""
    print("\nTesting threat detection check...")
    
    config = {
        'security': {
            'threat_detection': {
                'enabled': True
            }
        }
    }
    
    monitor = SecurityMonitor(config)
    result = monitor._check_threat_detection()
    
    assert result['status'] == 'PASS', "Threat detection check should pass"
    print("  ✓ Threat detection check works")


def test_comprehensive_security_check():
    """Test comprehensive security check"""
    print("\nTesting comprehensive security check...")
    
    # Load actual config
    config = Config("config.yml")
    
    monitor = SecurityMonitor(config)
    results = monitor.perform_security_check()
    
    assert results is not None, "Check should return results"
    assert 'timestamp' in results, "Results should have timestamp"
    assert 'checks' in results, "Results should have checks"
    assert 'violations' in results, "Results should have violations"
    assert 'overall_status' in results, "Results should have overall status"
    
    # Check that all expected checks were performed
    expected_checks = ['fips', 'password_policy', 'rate_limiting', 'audit_logging', 'threat_detection']
    for check in expected_checks:
        assert check in results['checks'], f"Check '{check}' should be present"
    
    print(f"  ✓ Comprehensive check works (status: {results['overall_status']})")
    print(f"    Checks performed: {len(results['checks'])}")
    print(f"    Violations found: {len(results['violations'])}")


def test_compliance_status():
    """Test compliance status tracking"""
    print("\nTesting compliance status tracking...")
    
    config = Config("config.yml")
    monitor = SecurityMonitor(config)
    
    # Perform check to update status
    monitor.perform_security_check()
    
    # Get compliance status
    status = monitor.get_compliance_status()
    
    assert status is not None, "Status should be returned"
    assert 'last_check' in status, "Status should have last_check"
    assert 'status' in status, "Status should have status dict"
    assert 'recent_violations' in status, "Status should have recent_violations"
    
    # Check status fields
    status_fields = ['fips_compliant', 'crypto_available', 'password_policy_active',
                     'rate_limiting_active', 'audit_logging_active', 'threat_detection_active']
    for field in status_fields:
        assert field in status['status'], f"Status should have '{field}' field"
    
    print("  ✓ Compliance status tracking works")
    print(f"    FIPS compliant: {status['status']['fips_compliant']}")
    print(f"    Crypto available: {status['status']['crypto_available']}")
    print(f"    Password policy active: {status['status']['password_policy_active']}")


def test_security_enforcement():
    """Test security enforcement"""
    print("\nTesting security enforcement...")
    
    config = Config("config.yml")
    monitor = SecurityMonitor(config)
    
    # Test enforcement
    can_continue = monitor.enforce_security_requirements()
    
    # Should return True unless critical FIPS failure with enforcement
    assert isinstance(can_continue, bool), "Enforcement should return boolean"
    
    if can_continue:
        print("  ✓ Security enforcement allows system to continue")
    else:
        print("  ✓ Security enforcement blocks system (critical violations)")


def test_monitor_lifecycle():
    """Test monitor start/stop lifecycle"""
    print("\nTesting monitor lifecycle...")
    
    config = Config("config.yml")
    monitor = SecurityMonitor(config)
    
    # Start monitor
    monitor.start()
    assert monitor.running, "Monitor should be running"
    assert monitor.monitor_thread is not None, "Monitor thread should exist"
    print("  ✓ Monitor starts successfully")
    
    # Let it run briefly (2 seconds to ensure thread is active)
    time.sleep(2)
    
    # Stop monitor
    monitor.stop()
    assert not monitor.running, "Monitor should be stopped"
    print("  ✓ Monitor stops successfully")


def test_get_security_monitor():
    """Test factory function"""
    print("\nTesting security monitor factory function...")
    
    config = Config("config.yml")
    monitor = get_security_monitor(config)
    
    assert monitor is not None, "Factory should return monitor"
    assert isinstance(monitor, SecurityMonitor), "Should return SecurityMonitor instance"
    
    print("  ✓ Factory function works")


def run_all_tests():
    """Run all security monitor tests"""
    print("=" * 60)
    print("Running Security Monitor Tests")
    print("=" * 60)
    
    tests = [
        test_security_monitor_initialization,
        test_fips_compliance_check,
        test_password_policy_check,
        test_rate_limiting_check,
        test_audit_logging_check,
        test_threat_detection_check,
        test_comprehensive_security_check,
        test_compliance_status,
        test_security_enforcement,
        test_monitor_lifecycle,
        test_get_security_monitor
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ All security monitor tests passed!")
    print("=" * 60)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
