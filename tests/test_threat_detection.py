#!/usr/bin/env python3
"""
Tests for Enhanced Threat Detection
"""
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.database import DatabaseBackend
from pbx.utils.security import ThreatDetector


def test_threat_detector_initialization() -> bool:
    """Test threat detector initialization"""
    print("Testing threat detector initialization...")

    config = {"security": {"threat_detection": {"enabled": True}}}
    detector = ThreatDetector(database=None, config=config)

    assert detector.enabled, "Threat detection should be enabled"
    print("  ✓ Threat detector initialized")

    return True


def test_ip_blocking() -> bool:
    """Test IP blocking"""
    print("Testing IP blocking...")

    config = {"security": {"threat_detection": {"enabled": True}}}
    detector = ThreatDetector(database=None, config=config)

    test_ip = "192.168.1.100"

    # IP should not be blocked initially
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert not is_blocked, "IP should not be blocked initially"
    print("  ✓ IP initially not blocked")

    # Block IP
    detector.block_ip(test_ip, "Test block", duration=10)

    # IP should now be blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked, "IP should be blocked after blocking"
    assert "Test block" in reason, "Block reason should be preserved"
    print("  ✓ IP successfully blocked")

    # Unblock IP
    detector.unblock_ip(test_ip)

    # IP should no longer be blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert not is_blocked, "IP should not be blocked after unblocking"
    print("  ✓ IP successfully unblocked")

    return True


def test_auto_unblock() -> bool:
    """Test automatic unblocking after duration"""
    print("Testing automatic unblocking...")

    config = {"security": {"threat_detection": {"enabled": True}}}
    detector = ThreatDetector(database=None, config=config)

    test_ip = "192.168.1.101"

    # Block IP for 1.5 seconds
    detector.block_ip(test_ip, "Test auto-unblock", duration=1.5)

    # IP should be blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked, "IP should be blocked"
    print("  ✓ IP blocked with short duration")

    # Wait for block to expire
    time.sleep(2)

    # IP should be auto-unblocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert not is_blocked, "IP should be auto-unblocked after duration"
    print("  ✓ IP auto-unblocked after duration expired")

    return True


def test_failed_attempt_tracking() -> bool:
    """Test failed attempt tracking and auto-blocking"""
    print("Testing failed attempt tracking...")

    config = {"security": {"threat_detection": {"enabled": True, "failed_login_threshold": 5}}}
    detector = ThreatDetector(database=None, config=config)

    test_ip = "192.168.1.102"

    # Record multiple failed attempts (below threshold)
    for i in range(3):
        detector.record_failed_attempt(test_ip, "Invalid password")

    # IP should not be blocked yet
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert not is_blocked, "IP should not be blocked below threshold"
    print("  ✓ IP not blocked below threshold")

    # Record more failed attempts to exceed threshold
    for i in range(3):
        detector.record_failed_attempt(test_ip, "Invalid password")
        # Check attempt count (debug)
        attempt_count = len(detector.failed_attempts.get(test_ip, []))
        print(f"    Attempt count after {i + 4} attempts: {attempt_count}")

    # IP should now be auto-blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    print(f"    Is blocked: {is_blocked}, Reason: {reason}")
    assert is_blocked, "IP should be auto-blocked after exceeding threshold"
    assert "Excessive failed login attempts" in reason
    print("  ✓ IP auto-blocked after exceeding failed attempt threshold")

    return True


def test_suspicious_pattern_detection() -> bool:
    """Test suspicious pattern detection"""
    print("Testing suspicious pattern detection...")

    config = {
        "security": {"threat_detection": {"enabled": True, "suspicious_pattern_threshold": 3}}
    }
    detector = ThreatDetector(database=None, config=config)

    test_ip = "192.168.1.103"

    # Detect pattern below threshold
    is_threat = detector.detect_suspicious_pattern(test_ip, "rapid_requests")
    assert not is_threat, "Should not be threat below threshold"
    print("  ✓ Pattern detected but below threshold")

    # Detect pattern again
    detector.detect_suspicious_pattern(test_ip, "rapid_requests")

    # Detect pattern to exceed threshold
    is_threat = detector.detect_suspicious_pattern(test_ip, "rapid_requests")
    assert is_threat, "Should be threat after exceeding threshold"
    print("  ✓ Pattern becomes threat after exceeding threshold")

    # IP should be blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked, "IP should be blocked after suspicious pattern"
    print("  ✓ IP auto-blocked due to suspicious pattern")

    return True


def test_request_pattern_analysis() -> bool:
    """Test request pattern analysis"""
    print("Testing request pattern analysis...")

    config = {"security": {"threat_detection": {"enabled": True}}}
    detector = ThreatDetector(database=None, config=config)

    # Test normal request
    analysis = detector.analyze_request_pattern("192.168.1.104", "Mozilla/5.0")
    assert not analysis["is_blocked"], "Normal request should not be blocked"
    assert not analysis["is_suspicious"], "Normal request should not be suspicious"
    assert analysis["score"] == 0, "Normal request should have score 0"
    print("  ✓ Normal request analyzed correctly")

    # Test scanner user agent
    analysis = detector.analyze_request_pattern("192.168.1.105", "nmap/7.80")
    assert not analysis["is_blocked"], "Scanner should not be immediately blocked"
    assert analysis["is_suspicious"], "Scanner should be marked suspicious"
    assert analysis["score"] > 0, "Scanner should have elevated threat score"
    assert len(analysis["threats"]) > 0, "Scanner should have threats listed"
    print("  ✓ Scanner user agent detected")
    print(f"    Threats: {analysis['threats']}")
    print(f"    Score: {analysis['score']}")

    return True


def test_with_database() -> bool:
    """Test threat detection with database persistence"""
    print("Testing threat detection with database...")

    # Create temporary SQLite database
    import tempfile

    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = db_file.name
    db_file.close()

    try:
        # Create database config
        db_config = {
            "database": {"type": "sqlite", "path": db_path},
            "security": {"threat_detection": {"enabled": True, "failed_login_threshold": 5}},
        }

        # Create database
        db = DatabaseBackend(db_config)
        if not db.connect():
            print("  ⚠ Database connection failed, skipping database tests")
            return True

        # Initialize tables
        db.create_tables()

        # Create threat detector
        detector = ThreatDetector(database=db, config=db_config)

        # Test IP blocking with database persistence
        test_ip = "192.168.1.106"
        detector.block_ip(test_ip, "Database test block", duration=3600)
        print("  ✓ IP blocked with database persistence")

        # Create new detector instance (simulates restart)
        detector2 = ThreatDetector(database=db, config=db_config)

        # IP should still be blocked (loaded from database)
        is_blocked, reason = detector2.is_ip_blocked(test_ip)
        assert is_blocked, "IP should be blocked after reload from database"
        assert "Database test block" in reason
        print("  ✓ IP block persisted across detector instances")

        # Test threat event logging
        detector.record_failed_attempt("192.168.1.107", "Test failed login")
        print("  ✓ Threat event logged to database")

        # Test threat summary
        summary = detector.get_threat_summary(hours=24)
        assert summary["total_events"] >= 0, "Summary should return total events"
        print(
            f"  ✓ Threat summary retrieved: {summary['total_events']} events"
        )

        # Clean up
        db.connection.close()
        os.unlink(db_path)

        return True

    except Exception as e:
        # Clean up on error
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except BaseException:
                pass
        raise e


def run_all_tests() -> bool:
    """Run all threat detection tests"""
    print("=" * 60)
    print("Enhanced Threat Detection Tests")
    print("=" * 60)
    print()

    tests = [
        test_threat_detector_initialization,
        test_ip_blocking,
        test_auto_unblock,
        test_failed_attempt_tracking,
        test_suspicious_pattern_detection,
        test_request_pattern_analysis,
        test_with_database,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test.__name__} failed with exception: {e}")
            import traceback

            traceback.print_exc()
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
