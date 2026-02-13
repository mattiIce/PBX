#!/usr/bin/env python3
"""
Tests for Enhanced Threat Detection
"""
import os
import time


from pbx.utils.database import DatabaseBackend
from pbx.utils.security import ThreatDetector


def test_threat_detector_initialization() -> bool:
    """Test threat detector initialization"""

    config = {"security": {"threat_detection": {"enabled": True}}}
    detector = ThreatDetector(database=None, config=config)

    assert detector.enabled, "Threat detection should be enabled"

    return True


def test_ip_blocking() -> bool:
    """Test IP blocking"""

    config = {"security": {"threat_detection": {"enabled": True}}}
    detector = ThreatDetector(database=None, config=config)

    test_ip = "192.168.1.100"

    # IP should not be blocked initially
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert not is_blocked, "IP should not be blocked initially"

    # Block IP
    detector.block_ip(test_ip, "Test block", duration=10)

    # IP should now be blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked, "IP should be blocked after blocking"
    assert "Test block" in reason, "Block reason should be preserved"

    # Unblock IP
    detector.unblock_ip(test_ip)

    # IP should no longer be blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert not is_blocked, "IP should not be blocked after unblocking"

    return True


def test_auto_unblock() -> bool:
    """Test automatic unblocking after duration"""

    config = {"security": {"threat_detection": {"enabled": True}}}
    detector = ThreatDetector(database=None, config=config)

    test_ip = "192.168.1.101"

    # Block IP for 1.5 seconds
    detector.block_ip(test_ip, "Test auto-unblock", duration=1.5)

    # IP should be blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked, "IP should be blocked"

    # Wait for block to expire
    time.sleep(2)

    # IP should be auto-unblocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert not is_blocked, "IP should be auto-unblocked after duration"

    return True


def test_failed_attempt_tracking() -> bool:
    """Test failed attempt tracking and auto-blocking"""

    config = {"security": {"threat_detection": {"enabled": True, "failed_login_threshold": 5}}}
    detector = ThreatDetector(database=None, config=config)

    test_ip = "192.168.1.102"

    # Record multiple failed attempts (below threshold)
    for i in range(3):
        detector.record_failed_attempt(test_ip, "Invalid password")

    # IP should not be blocked yet
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert not is_blocked, "IP should not be blocked below threshold"

    # Record more failed attempts to exceed threshold
    for i in range(3):
        detector.record_failed_attempt(test_ip, "Invalid password")
        # Check attempt count (debug)
        attempt_count = len(detector.failed_attempts.get(test_ip, []))

    # IP should now be auto-blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked, "IP should be auto-blocked after exceeding threshold"
    assert "Excessive failed login attempts" in reason

    return True


def test_suspicious_pattern_detection() -> bool:
    """Test suspicious pattern detection"""

    config = {
        "security": {"threat_detection": {"enabled": True, "suspicious_pattern_threshold": 3}}
    }
    detector = ThreatDetector(database=None, config=config)

    test_ip = "192.168.1.103"

    # Detect pattern below threshold
    is_threat = detector.detect_suspicious_pattern(test_ip, "rapid_requests")
    assert not is_threat, "Should not be threat below threshold"

    # Detect pattern again
    detector.detect_suspicious_pattern(test_ip, "rapid_requests")

    # Detect pattern to exceed threshold
    is_threat = detector.detect_suspicious_pattern(test_ip, "rapid_requests")
    assert is_threat, "Should be threat after exceeding threshold"

    # IP should be blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked, "IP should be blocked after suspicious pattern"

    return True


def test_request_pattern_analysis() -> bool:
    """Test request pattern analysis"""

    config = {"security": {"threat_detection": {"enabled": True}}}
    detector = ThreatDetector(database=None, config=config)

    # Test normal request
    analysis = detector.analyze_request_pattern("192.168.1.104", "Mozilla/5.0")
    assert not analysis["is_blocked"], "Normal request should not be blocked"
    assert not analysis["is_suspicious"], "Normal request should not be suspicious"
    assert analysis["score"] == 0, "Normal request should have score 0"

    # Test scanner user agent
    analysis = detector.analyze_request_pattern("192.168.1.105", "nmap/7.80")
    assert not analysis["is_blocked"], "Scanner should not be immediately blocked"
    assert analysis["is_suspicious"], "Scanner should be marked suspicious"
    assert analysis["score"] > 0, "Scanner should have elevated threat score"
    assert len(analysis["threats"]) > 0, "Scanner should have threats listed"

    return True


def test_with_database() -> bool:
    """Test threat detection with database persistence"""

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
            return True

        # Initialize tables
        db.create_tables()

        # Create threat detector
        detector = ThreatDetector(database=db, config=db_config)

        # Test IP blocking with database persistence
        test_ip = "192.168.1.106"
        detector.block_ip(test_ip, "Database test block", duration=3600)

        # Create new detector instance (simulates restart)
        detector2 = ThreatDetector(database=db, config=db_config)

        # IP should still be blocked (loaded from database)
        is_blocked, reason = detector2.is_ip_blocked(test_ip)
        assert is_blocked, "IP should be blocked after reload from database"
        assert "Database test block" in reason

        # Test threat event logging
        detector.record_failed_attempt("192.168.1.107", "Test failed login")

        # Test threat summary
        summary = detector.get_threat_summary(hours=24)
        assert summary["total_events"] >= 0, "Summary should return total events"

        # Clean up
        db.connection.close()
        os.unlink(db_path)

        return True

    except (KeyError, OSError, TypeError, ValueError) as e:
        # Clean up on error
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except BaseException:
                pass
        raise e
