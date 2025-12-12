#!/usr/bin/env python3
"""
Tests for Kari's Law compliance module

Kari's Law requires multi-line telephone systems (MLTS) to:
1. Allow direct dialing of 911 without prefix
2. Route emergency calls immediately
3. Notify designated contacts automatically
"""
import os
import sys
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.karis_law import KarisLawCompliance


def create_mock_pbx():
    """Create mock PBX core for testing"""
    pbx = MagicMock()
    
    # Mock extension registry
    pbx.extension_registry = MagicMock()
    pbx.extension_registry.get_extension = MagicMock(return_value={
        'extension': '1001',
        'name': 'Test User',
        'email': 'test@example.com',
        'department': 'Engineering'
    })
    
    # Mock trunk system
    pbx.trunk_system = MagicMock()
    pbx.trunk_system.route_outbound = MagicMock(return_value=(MagicMock(trunk_id='test_trunk', name='Test Trunk', can_make_call=lambda: True), '911'))
    pbx.trunk_system.get_trunk = MagicMock(return_value=MagicMock(trunk_id='emergency_trunk', name='Emergency Trunk', can_make_call=lambda: True))
    
    # Mock emergency notification
    pbx.emergency_notification = MagicMock()
    pbx.emergency_notification.enabled = True
    pbx.emergency_notification.on_911_call = MagicMock()
    
    # Mock E911 location
    pbx.e911_location = MagicMock()
    pbx.e911_location.enabled = True
    pbx.e911_location.get_location = MagicMock(return_value={
        'building': 'Building A',
        'floor': '2',
        'room': '205',
        'dispatchable_location': 'Building A, Floor 2, Room 205, 123 Main St, City, State 12345'
    })
    
    return pbx


def test_emergency_number_detection():
    """Test that emergency numbers are correctly detected"""
    print("Testing emergency number detection...")
    
    pbx = create_mock_pbx()
    karis_law = KarisLawCompliance(pbx)
    
    # Test direct 911 (Kari's Law compliant)
    assert karis_law.is_emergency_number('911'), "Should detect direct 911"
    assert karis_law.is_direct_911('911'), "Should detect direct 911"
    
    # Test legacy prefixed numbers (should still be detected)
    assert karis_law.is_emergency_number('9911'), "Should detect 9911"
    assert karis_law.is_emergency_number('9-911'), "Should detect 9-911"
    assert not karis_law.is_direct_911('9911'), "9911 is not direct 911"
    assert not karis_law.is_direct_911('9-911'), "9-911 is not direct 911"
    
    # Test non-emergency numbers
    assert not karis_law.is_emergency_number('1001'), "Should not detect internal extension"
    assert not karis_law.is_emergency_number('5551234567'), "Should not detect regular number"
    assert not karis_law.is_emergency_number('811'), "Should not detect 811"
    assert not karis_law.is_emergency_number('9111'), "Should not detect 9111"
    
    print("✓ Emergency number detection works correctly")


def test_emergency_number_normalization():
    """Test normalization of emergency numbers"""
    print("Testing emergency number normalization...")
    
    pbx = create_mock_pbx()
    karis_law = KarisLawCompliance(pbx)
    
    # Test normalization of various formats
    assert karis_law.normalize_emergency_number('911') == '911', "911 should remain 911"
    assert karis_law.normalize_emergency_number('9911') == '911', "9911 should normalize to 911"
    assert karis_law.normalize_emergency_number('9-911') == '911', "9-911 should normalize to 911"
    
    # Non-emergency numbers should remain unchanged
    assert karis_law.normalize_emergency_number('1001') == '1001', "Regular number should not change"
    
    print("✓ Emergency number normalization works correctly")


def test_direct_911_dialing():
    """Test direct 911 dialing (Kari's Law requirement)"""
    print("Testing direct 911 dialing...")
    
    pbx = create_mock_pbx()
    config = {
        'features': {
            'karis_law': {
                'enabled': True,
                'auto_notify': True,
                'emergency_trunk_id': 'emergency_trunk'
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)
    
    # Test direct 911 call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension='1001',
        dialed_number='911',
        call_id='test-call-1',
        from_addr=('192.168.1.100', 5060)
    )
    
    assert success, "Direct 911 call should succeed"
    assert routing_info['success'], "Routing should succeed"
    assert routing_info['trunk_id'] == 'emergency_trunk', "Should use emergency trunk"
    assert routing_info['destination'] == '911', "Destination should be 911"
    
    # Verify emergency notification was triggered
    assert pbx.emergency_notification.on_911_call.called, "Emergency notification should be triggered"
    
    print("✓ Direct 911 dialing works correctly")


def test_legacy_prefix_support():
    """Test that legacy prefixes (9911, 9-911) still work but are normalized"""
    print("Testing legacy prefix support...")
    
    pbx = create_mock_pbx()
    config = {
        'features': {
            'karis_law': {
                'enabled': True,
                'auto_notify': True
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)
    
    # Test 9911
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension='1001',
        dialed_number='9911',
        call_id='test-call-2',
        from_addr=('192.168.1.100', 5060)
    )
    
    assert success, "9911 call should succeed"
    assert routing_info['destination'] == '911', "Should normalize to 911"
    
    # Test 9-911
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension='1001',
        dialed_number='9-911',
        call_id='test-call-3',
        from_addr=('192.168.1.100', 5060)
    )
    
    assert success, "9-911 call should succeed"
    assert routing_info['destination'] == '911', "Should normalize to 911"
    
    print("✓ Legacy prefix support works correctly")


def test_automatic_notification():
    """Test automatic notification to designated contacts"""
    print("Testing automatic notification...")
    
    pbx = create_mock_pbx()
    config = {
        'features': {
            'karis_law': {
                'enabled': True,
                'auto_notify': True
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)
    
    # Make emergency call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension='1001',
        dialed_number='911',
        call_id='test-call-4',
        from_addr=('192.168.1.100', 5060)
    )
    
    assert success, "Emergency call should succeed"
    
    # Verify notification was triggered
    assert pbx.emergency_notification.on_911_call.called, "Notification should be triggered"
    
    # Verify notification details
    call_args = pbx.emergency_notification.on_911_call.call_args
    assert call_args[1]['caller_extension'] == '1001', "Should include caller extension"
    assert call_args[1]['caller_name'] == 'Test User', "Should include caller name"
    assert 'location' in call_args[1], "Should include location"
    
    print("✓ Automatic notification works correctly")


def test_location_information():
    """Test location information provision (Ray Baum's Act)"""
    print("Testing location information provision...")
    
    pbx = create_mock_pbx()
    config = {
        'features': {
            'karis_law': {
                'enabled': True,
                'require_location': True
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)
    
    # Get location info
    location = karis_law._get_location_info('1001')
    
    assert location is not None, "Location should be available"
    assert 'building' in location, "Should include building"
    assert 'dispatchable_location' in location, "Should include dispatchable location"
    
    print("✓ Location information provision works correctly")


def test_emergency_call_history():
    """Test emergency call history tracking"""
    print("Testing emergency call history...")
    
    pbx = create_mock_pbx()
    karis_law = KarisLawCompliance(pbx)
    
    # Make multiple emergency calls
    for i in range(3):
        karis_law.handle_emergency_call(
            caller_extension=f'100{i}',
            dialed_number='911',
            call_id=f'test-call-{i}',
            from_addr=('192.168.1.100', 5060)
        )
    
    # Get history
    history = karis_law.get_emergency_call_history()
    
    assert len(history) == 3, "Should have 3 calls in history"
    
    # Test filtering by extension
    history_filtered = karis_law.get_emergency_call_history(extension='1001')
    assert len(history_filtered) == 1, "Should have 1 call from extension 1001"
    
    print("✓ Emergency call history tracking works correctly")


def test_compliance_validation():
    """Test compliance validation"""
    print("Testing compliance validation...")
    
    pbx = create_mock_pbx()
    config = {
        'features': {
            'karis_law': {
                'enabled': True,
                'emergency_trunk_id': 'emergency_trunk'
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)
    
    # Validate compliance
    results = karis_law.validate_compliance()
    
    assert results['compliant'], "Should be compliant"
    assert len(results['errors']) == 0, "Should have no errors"
    
    print("✓ Compliance validation works correctly")


def test_disabled_compliance():
    """Test behavior when compliance is disabled"""
    print("Testing disabled compliance...")
    
    pbx = create_mock_pbx()
    config = {
        'features': {
            'karis_law': {
                'enabled': False
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)
    
    # Try to make emergency call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension='1001',
        dialed_number='911',
        call_id='test-call-disabled',
        from_addr=('192.168.1.100', 5060)
    )
    
    assert not success, "Call should fail when compliance is disabled"
    assert 'error' in routing_info, "Should have error message"
    
    # Validate should show non-compliant
    results = karis_law.validate_compliance()
    assert not results['compliant'], "Should not be compliant"
    assert "disabled" in results['errors'][0].lower(), "Error should mention disabled"
    
    print("✓ Disabled compliance behavior works correctly")


def test_no_trunk_available():
    """Test behavior when no trunk is available"""
    print("Testing no trunk available scenario...")
    
    pbx = create_mock_pbx()
    pbx.trunk_system.route_outbound = MagicMock(return_value=(None, None))
    pbx.trunk_system.get_trunk = MagicMock(return_value=None)
    
    karis_law = KarisLawCompliance(pbx)
    
    # Try to make emergency call
    success, routing_info = karis_law.handle_emergency_call(
        caller_extension='1001',
        dialed_number='911',
        call_id='test-call-no-trunk',
        from_addr=('192.168.1.100', 5060)
    )
    
    # Call should succeed but routing should fail
    assert success, "Call handling should complete"
    assert not routing_info['success'], "Routing should fail"
    assert 'error' in routing_info, "Should have error message"
    
    print("✓ No trunk available scenario works correctly")


def test_statistics():
    """Test statistics reporting"""
    print("Testing statistics...")
    
    pbx = create_mock_pbx()
    config = {
        'features': {
            'karis_law': {
                'enabled': True,
                'auto_notify': True,
                'require_location': True,
                'emergency_trunk_id': 'emergency_trunk'
            }
        }
    }
    karis_law = KarisLawCompliance(pbx, config)
    
    # Make some calls
    karis_law.handle_emergency_call('1001', '911', 'call-1', ('192.168.1.100', 5060))
    karis_law.handle_emergency_call('1002', '911', 'call-2', ('192.168.1.101', 5060))
    
    # Get statistics
    stats = karis_law.get_statistics()
    
    assert stats['enabled'], "Should be enabled"
    assert stats['total_emergency_calls'] == 2, "Should have 2 calls"
    assert stats['auto_notify'], "Auto-notify should be enabled"
    assert stats['require_location'], "Location should be required"
    assert stats['emergency_trunk_configured'], "Emergency trunk should be configured"
    
    print("✓ Statistics reporting works correctly")


def run_all_tests():
    """Run all Kari's Law tests"""
    print("=" * 70)
    print("Kari's Law Compliance Tests")
    print("=" * 70)
    print()
    
    tests = [
        test_emergency_number_detection,
        test_emergency_number_normalization,
        test_direct_911_dialing,
        test_legacy_prefix_support,
        test_automatic_notification,
        test_location_information,
        test_emergency_call_history,
        test_compliance_validation,
        test_disabled_compliance,
        test_no_trunk_available,
        test_statistics,
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
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
