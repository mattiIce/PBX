#!/usr/bin/env python3
"""
Tests for E911 protection system
Ensures that emergency (911) calls are never placed during testing
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.e911_protection import E911Protection
from pbx.features.sip_trunk import SIPTrunkSystem, SIPTrunk, OutboundRule


def test_e911_pattern_detection():
    """Test that E911 patterns are correctly detected"""
    print("Testing E911 pattern detection...")
    
    protection = E911Protection()
    
    # Test standard 911
    assert protection.is_e911_number("911"), "Should detect standard 911"
    
    # Test enhanced 911 with prefix
    assert protection.is_e911_number("1911"), "Should detect enhanced 911"
    assert protection.is_e911_number("12911"), "Should detect enhanced 911 with longer prefix"
    
    # Test non-emergency numbers
    assert not protection.is_e911_number("1001"), "Should not detect internal extension"
    assert not protection.is_e911_number("5551234567"), "Should not detect regular number"
    assert not protection.is_e911_number("9111"), "Should not detect 9111"
    assert not protection.is_e911_number("811"), "Should not detect 811"
    
    print("✓ E911 pattern detection works correctly")


def test_e911_blocking_in_test_mode():
    """Test that E911 calls are blocked when in test mode"""
    print("Testing E911 blocking in test mode...")
    
    # Set test mode environment variable
    os.environ['TEST_MODE'] = '1'
    
    protection = E911Protection()
    
    # Verify test mode is detected
    assert protection.is_test_mode(), "Should be in test mode"
    
    # Test that 911 is blocked
    assert protection.block_if_e911("911", "test context"), "Should block 911 in test mode"
    assert protection.block_if_e911("1911", "test context"), "Should block enhanced 911 in test mode"
    
    # Test that non-emergency numbers are not blocked
    assert not protection.block_if_e911("1001", "test context"), "Should not block internal extension"
    assert not protection.block_if_e911("5551234567", "test context"), "Should not block regular number"
    
    # Clean up
    del os.environ['TEST_MODE']
    
    print("✓ E911 blocking in test mode works correctly")


def test_e911_warning_in_production_mode():
    """Test that E911 calls generate warnings but are not blocked in production"""
    print("Testing E911 warning in production mode...")
    
    # Ensure we're not in test mode
    for var in ['TEST_MODE', 'TESTING', 'PYTEST_CURRENT_TEST', 'PBX_TEST_MODE']:
        if var in os.environ:
            del os.environ[var]
    
    protection = E911Protection()
    
    # Verify we're not in test mode
    assert not protection.is_test_mode(), "Should not be in test mode"
    
    # Test that 911 is NOT blocked in production (only warned)
    assert not protection.block_if_e911("911", "production context"), "Should NOT block 911 in production"
    assert not protection.block_if_e911("1911", "production context"), "Should NOT block enhanced 911 in production"
    
    print("✓ E911 warning in production mode works correctly")


def test_sip_trunk_e911_blocking():
    """Test that SIP trunk system blocks E911 calls in test mode"""
    print("Testing SIP trunk E911 blocking...")
    
    # Set test mode
    os.environ['TEST_MODE'] = '1'
    
    # Create SIP trunk system
    trunk_system = SIPTrunkSystem()
    
    # Add a test trunk
    from pbx.features.sip_trunk import TrunkStatus
    
    trunk = SIPTrunk(
        trunk_id="test_trunk",
        name="Test Trunk",
        host="test.sip.provider.com",
        username="test",
        password="test"
    )
    trunk.status = TrunkStatus.REGISTERED
    trunk.channels_available = 10
    trunk_system.add_trunk(trunk)
    
    # Add outbound rule for 911
    rule = OutboundRule(
        rule_id="emergency",
        pattern="^911$",
        trunk_id="test_trunk"
    )
    trunk_system.add_outbound_rule(rule)
    
    # Try to route 911 call - should be blocked
    routed_trunk, transformed_number = trunk_system.route_outbound("911")
    assert routed_trunk is None, "911 call should be blocked in test mode"
    assert transformed_number is None, "911 call should return None for transformed number"
    
    # Try to make 911 call - should be blocked
    result = trunk_system.make_outbound_call("1001", "911")
    assert not result, "911 call should fail in test mode"
    
    # Regular call should work
    regular_rule = OutboundRule(
        rule_id="regular",
        pattern="^[2-9][0-9]{9}$",
        trunk_id="test_trunk"
    )
    trunk_system.add_outbound_rule(regular_rule)
    
    routed_trunk, transformed_number = trunk_system.route_outbound("5551234567")
    assert routed_trunk is not None, "Regular call should work"
    assert transformed_number == "5551234567", "Regular number should be routed"
    
    # Clean up
    del os.environ['TEST_MODE']
    
    print("✓ SIP trunk E911 blocking works correctly")


def test_test_mode_detection():
    """Test various methods of test mode detection"""
    print("Testing test mode detection...")
    
    # Clean environment first
    for var in ['TEST_MODE', 'TESTING', 'PYTEST_CURRENT_TEST', 'PBX_TEST_MODE']:
        if var in os.environ:
            del os.environ[var]
    
    # Test without any test indicators
    protection = E911Protection()
    assert not protection.is_test_mode(), "Should not be in test mode without indicators"
    
    # Test with TEST_MODE
    os.environ['TEST_MODE'] = '1'
    protection = E911Protection()
    assert protection.is_test_mode(), "Should detect TEST_MODE"
    del os.environ['TEST_MODE']
    
    # Test with TESTING
    os.environ['TESTING'] = 'true'
    protection = E911Protection()
    assert protection.is_test_mode(), "Should detect TESTING"
    del os.environ['TESTING']
    
    # Test with PYTEST_CURRENT_TEST
    os.environ['PYTEST_CURRENT_TEST'] = 'test_e911_protection.py::test_test_mode_detection'
    protection = E911Protection()
    assert protection.is_test_mode(), "Should detect PYTEST_CURRENT_TEST"
    del os.environ['PYTEST_CURRENT_TEST']
    
    # Test with PBX_TEST_MODE
    os.environ['PBX_TEST_MODE'] = '1'
    protection = E911Protection()
    assert protection.is_test_mode(), "Should detect PBX_TEST_MODE"
    del os.environ['PBX_TEST_MODE']
    
    print("✓ Test mode detection works correctly")


def run_all_tests():
    """Run all E911 protection tests"""
    print("=" * 60)
    print("E911 Protection Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_e911_pattern_detection,
        test_test_mode_detection,
        test_e911_blocking_in_test_mode,
        test_e911_warning_in_production_mode,
        test_sip_trunk_e911_blocking,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
