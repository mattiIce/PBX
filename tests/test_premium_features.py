#!/usr/bin/env python3
"""
Tests for premium features
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.analytics import AnalyticsEngine
from pbx.features.licensing import LicenseManager, LicenseType, FeatureFlag
from pbx.features.rbac import RBACManager, Role, Permission


def test_licensing():
    """Test licensing system"""
    print("Testing licensing system...")
    
    config = {
        'licensing.license_file': '/tmp/test_license.json',
        'licensing.usage_file': '/tmp/test_usage.json'
    }
    
    # Clean up any existing test files
    for f in [config['licensing.license_file'], config['licensing.usage_file']]:
        if os.path.exists(f):
            os.remove(f)
    
    manager = LicenseManager(config)
    
    # Test default (FREE) tier
    assert manager.get_license_tier() == LicenseType.FREE
    assert not manager.has_feature(FeatureFlag.ADVANCED_ANALYTICS)
    
    # Test license update to Professional
    new_license = {
        'tier': LicenseType.PROFESSIONAL,
        'organization': 'Test Company',
        'issued_date': datetime.now().isoformat(),
        'expiry_date': (datetime.now() + timedelta(days=365)).isoformat(),
        'custom_features': []
    }
    
    manager.update_license('TEST-KEY-123', new_license)
    assert manager.get_license_tier() == LicenseType.PROFESSIONAL
    assert manager.has_feature(FeatureFlag.ADVANCED_ANALYTICS)
    assert manager.has_feature(FeatureFlag.VOICEMAIL_TRANSCRIPTION)
    assert not manager.has_feature(FeatureFlag.AI_ROUTING)  # Enterprise only
    
    # Test limits
    assert manager.get_limit('max_extensions') == 100
    assert manager.check_limit('max_extensions', 50)
    assert not manager.check_limit('max_extensions', 150)
    
    # Test API rate limiting
    assert manager.can_make_api_call()
    for _ in range(100):  # Make some calls
        manager.track_api_call()
    
    # Clean up
    for f in [config['licensing.license_file'], config['licensing.usage_file']]:
        if os.path.exists(f):
            os.remove(f)
    
    print("✓ Licensing system works")


def test_rbac():
    """Test RBAC system"""
    print("Testing RBAC system...")
    
    config = {
        'rbac.users_file': '/tmp/test_users.json'
    }
    
    # Clean up any existing test file
    if os.path.exists(config['rbac.users_file']):
        os.remove(config['rbac.users_file'])
    
    manager = RBACManager(config)
    
    # Test default admin user
    user = manager.authenticate('admin', 'admin123')
    assert user is not None
    assert user['role'] == Role.SUPER_ADMIN
    
    # Test permission checking
    assert manager.has_permission('admin', Permission.VIEW_DASHBOARD)
    assert manager.has_permission('admin', Permission.SYSTEM_ADMIN)
    
    # Create a supervisor user
    assert manager.create_user('supervisor1', 'pass123', Role.SUPERVISOR, 'super@test.com')
    
    # Test supervisor authentication
    user = manager.authenticate('supervisor1', 'pass123')
    assert user is not None
    assert user['role'] == Role.SUPERVISOR
    
    # Test supervisor permissions
    assert manager.has_permission('supervisor1', Permission.VIEW_DASHBOARD)
    assert manager.has_permission('supervisor1', Permission.MONITOR_CALLS)
    assert not manager.has_permission('supervisor1', Permission.SYSTEM_ADMIN)
    
    # Test session management
    token = manager.create_session('supervisor1')
    assert token is not None
    
    username = manager.validate_session(token)
    assert username == 'supervisor1'
    
    manager.destroy_session(token)
    assert manager.validate_session(token) is None
    
    # Test user update
    assert manager.update_user('supervisor1', role=Role.ADMIN)
    assert manager.users['supervisor1']['role'] == Role.ADMIN
    
    # Clean up
    if os.path.exists(config['rbac.users_file']):
        os.remove(config['rbac.users_file'])
    
    print("✓ RBAC system works")


def test_analytics():
    """Test analytics engine"""
    print("Testing analytics engine...")
    
    config = {
        'cdr.directory': '/tmp/test_cdr'
    }
    
    # Create test CDR directory
    os.makedirs(config['cdr.directory'], exist_ok=True)
    
    # Create sample CDR data
    today = datetime.now()
    cdr_file = os.path.join(config['cdr.directory'], f"cdr_{today.strftime('%Y-%m-%d')}.jsonl")
    
    sample_records = [
        {
            'call_id': 'test-1',
            'from': '1001',
            'to': '1002',
            'start_time': (today - timedelta(hours=2)).isoformat(),
            'disposition': 'ANSWERED',
            'duration': 120
        },
        {
            'call_id': 'test-2',
            'from': '1001',
            'to': '1003',
            'start_time': (today - timedelta(hours=1)).isoformat(),
            'disposition': 'ANSWERED',
            'duration': 300
        },
        {
            'call_id': 'test-3',
            'from': '1002',
            'to': '1001',
            'start_time': today.isoformat(),
            'disposition': 'MISSED',
            'duration': 0
        }
    ]
    
    with open(cdr_file, 'w') as f:
        for record in sample_records:
            f.write(json.dumps(record) + '\n')
    
    # Test analytics
    engine = AnalyticsEngine(config)
    
    # Test call volume by hour
    volume = engine.get_call_volume_by_hour(days=1)
    assert isinstance(volume, dict)
    assert len(volume) > 0
    
    # Test extension statistics
    stats = engine.get_extension_statistics('1001', days=1)
    assert stats['extension'] == '1001'
    assert stats['total_calls'] == 3  # 2 outbound, 1 inbound
    assert stats['outbound_calls'] == 2
    assert stats['inbound_calls'] == 1
    
    # Test executive summary
    summary = engine.generate_executive_summary(days=1)
    assert 'overview' in summary
    assert 'period' in summary
    assert summary['overview']['total_calls'] == 3
    
    # Clean up
    if os.path.exists(cdr_file):
        os.remove(cdr_file)
    os.rmdir(config['cdr.directory'])
    
    print("✓ Analytics engine works")


def run_all_tests():
    """Run all premium feature tests"""
    print("=" * 60)
    print("Running Premium Features Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_licensing,
        test_rbac,
        test_analytics
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
