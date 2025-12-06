#!/usr/bin/env python3
"""
Tests for stub feature implementations
"""
import sys
import os
import json
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.operator_console import OperatorConsole
from pbx.features.voicemail import VoicemailSystem, VoicemailIVR
from pbx.utils.dtmf import DTMFDetector, DTMFGenerator
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""
    def __init__(self):
        self.extension_registry = MockExtensionRegistry()
        self.call_manager = MockCallManager()
        self.parking_system = MockParkingSystem()


class MockExtensionRegistry:
    """Mock extension registry"""
    def get_all(self):
        return [
            MockExtension('1001', 'Test User 1', True),
            MockExtension('1002', 'Test User 2', False),
        ]
    
    def get(self, number):
        if number == '1001':
            return MockExtension('1001', 'Test User 1', True)
        return None


class MockExtension:
    """Mock extension"""
    def __init__(self, number, name, registered):
        self.number = number
        self.name = name
        self.registered = registered
        self.config = {'email': f'user{number}@test.com'}


class MockCallManager:
    """Mock call manager"""
    def __init__(self):
        self.active_calls = []
    
    def get_active_calls(self):
        return self.active_calls
    
    def get_call(self, call_id):
        return None


class MockParkingSystem:
    """Mock parking system"""
    def park_call(self, call_id):
        return "70"


def test_vip_caller_database():
    """Test VIP caller database functionality"""
    print("Testing VIP caller database...")
    
    # Create temporary directory for VIP database
    with tempfile.TemporaryDirectory() as tmpdir:
        vip_db_path = os.path.join(tmpdir, 'vip_test.json')
        
        config = {
            'features.operator_console.enabled': True,
            'features.operator_console.operator_extensions': ['1000'],
            'features.operator_console.vip_db_path': vip_db_path
        }
        
        pbx_core = MockPBXCore()
        console = OperatorConsole(config, pbx_core)
        
        # Test marking a caller as VIP
        assert console.mark_vip_caller('555-1234', priority_level=1, name='Important Client', 
                                      notes='Key account')
        
        # Test retrieving VIP caller
        vip = console.get_vip_caller('5551234')  # Test normalization
        assert vip is not None
        assert vip['name'] == 'Important Client'
        assert vip['priority_level'] == 1
        
        # Test checking VIP status
        assert console.is_vip_caller('555-1234')
        assert not console.is_vip_caller('555-9999')
        
        # Test listing VIP callers
        vips = console.list_vip_callers()
        assert len(vips) == 1
        
        # Test removing VIP status
        assert console.unmark_vip_caller('555-1234')
        assert not console.is_vip_caller('555-1234')
        
        # Verify persistence
        console2 = OperatorConsole(config, pbx_core)
        assert not console2.is_vip_caller('555-1234')
        
    print("✓ VIP caller database works")


def test_dtmf_detection():
    """Test DTMF tone detection"""
    print("Testing DTMF detection...")
    
    detector = DTMFDetector(sample_rate=8000, samples_per_frame=205)
    generator = DTMFGenerator(sample_rate=8000)
    
    # Test single digit detection
    for digit in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '#']:
        samples = generator.generate_tone(digit, duration_ms=100)
        detected = detector.detect_tone(samples)
        assert detected == digit, f"Expected {digit}, got {detected}"
    
    print("✓ DTMF single digit detection works")
    
    # Test sequence detection
    test_sequence = '12345'
    sequence_samples = generator.generate_sequence(test_sequence, tone_ms=100, gap_ms=50)
    detected_sequence = detector.detect_sequence(sequence_samples)
    assert test_sequence in detected_sequence, f"Expected {test_sequence} in {detected_sequence}"
    
    print("✓ DTMF sequence detection works")


def test_voicemail_ivr():
    """Test voicemail IVR state machine"""
    print("Testing voicemail IVR...")
    
    # Create temporary voicemail system
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.__new__(Config)
        config._config = {
            'extensions': [
                {'number': '1001', 'name': 'Test User', 'voicemail_pin': '1234'}
            ]
        }
        config.get = lambda key, default=None: config._config.get(key, default)
        config.get_extension = lambda num: next((e for e in config._config['extensions'] if e['number'] == num), None)
        
        vm_system = VoicemailSystem(storage_path=tmpdir, config=config)
        ivr = VoicemailIVR(vm_system, '1001')
        
        # Test initial state
        assert ivr.state == VoicemailIVR.STATE_WELCOME
        
        # Test PIN entry flow
        result = ivr.handle_dtmf('1')
        assert ivr.state == VoicemailIVR.STATE_PIN_ENTRY
        
        # Test transition to main menu (simulated PIN acceptance)
        ivr.state = VoicemailIVR.STATE_MAIN_MENU
        result = ivr.handle_dtmf('1')  # Listen to messages
        assert result['action'] in ['play_message', 'play_prompt']
        
        # Test options menu
        ivr.state = VoicemailIVR.STATE_MAIN_MENU
        result = ivr.handle_dtmf('2')
        assert result['action'] == 'play_prompt'
        assert 'options' in result['prompt']
        
        # Test exit
        ivr.state = VoicemailIVR.STATE_MAIN_MENU
        result = ivr.handle_dtmf('*')
        assert result['action'] == 'hangup'
        assert ivr.state == VoicemailIVR.STATE_GOODBYE
        
    print("✓ Voicemail IVR works")


def test_operator_console_features():
    """Test operator console features"""
    print("Testing operator console features...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        vip_db_path = os.path.join(tmpdir, 'vip_test.json')
        
        config = {
            'features.operator_console.enabled': True,
            'features.operator_console.operator_extensions': ['1000'],
            'features.operator_console.blf_monitoring': True,
            'features.operator_console.vip_db_path': vip_db_path
        }
        
        pbx_core = MockPBXCore()
        console = OperatorConsole(config, pbx_core)
        
        # Test operator authorization
        assert console.is_operator('1000')
        assert not console.is_operator('1001')
        
        # Test BLF status
        status = console.get_blf_status('1001')
        assert status in ['available', 'offline', 'busy', 'ringing', 'dnd']
        
        # Test directory lookup
        directory = console.get_directory()
        assert len(directory) >= 2
        assert any(e['extension'] == '1001' for e in directory)
        
        # Test directory search
        search_results = console.get_directory('Test User 1')
        assert len(search_results) >= 1
        assert search_results[0]['extension'] == '1001'
        
        # Test park and page
        slot = console.park_and_page('test-call-123', 'John Smith on line 1', page_method='log')
        assert slot == '70'
        
    print("✓ Operator console features work")


def test_integration_stubs():
    """Test that integration stubs are properly structured"""
    print("Testing integration stubs...")
    
    from pbx.integrations.zoom import ZoomIntegration
    from pbx.integrations.active_directory import ActiveDirectoryIntegration
    from pbx.integrations.outlook import OutlookIntegration
    from pbx.integrations.teams import TeamsIntegration
    
    # Test Zoom integration structure
    config = {
        'integrations.zoom.enabled': False,
        'integrations.zoom.account_id': 'test',
        'integrations.zoom.client_id': 'test',
        'integrations.zoom.client_secret': 'test'
    }
    zoom = ZoomIntegration(config)
    assert hasattr(zoom, 'authenticate')
    assert hasattr(zoom, 'create_meeting')
    
    # Test AD integration structure
    ad_config = {
        'integrations.active_directory.enabled': False,
        'integrations.active_directory.server': 'ldap://test.local',
        'integrations.active_directory.base_dn': 'DC=test,DC=local'
    }
    ad = ActiveDirectoryIntegration(ad_config)
    assert hasattr(ad, 'connect')
    assert hasattr(ad, 'authenticate_user')
    assert hasattr(ad, 'search_users')
    
    # Test Outlook integration structure
    outlook_config = {'integrations.outlook.enabled': False}
    outlook = OutlookIntegration(outlook_config)
    assert hasattr(outlook, 'authenticate')
    
    # Test Teams integration structure
    teams_config = {'integrations.teams.enabled': False}
    teams = TeamsIntegration(teams_config)
    assert hasattr(teams, 'authenticate')
    
    print("✓ Integration stubs properly structured")


def test_new_integration_implementations():
    """Test newly implemented integration features"""
    print("Testing newly implemented integration features...")
    
    from pbx.integrations.zoom import ZoomIntegration
    from pbx.integrations.active_directory import ActiveDirectoryIntegration
    from pbx.integrations.outlook import OutlookIntegration
    from pbx.integrations.teams import TeamsIntegration
    
    # Test Zoom - get_phone_user_status implementation
    zoom_config = {
        'integrations.zoom.enabled': False,
        'integrations.zoom.account_id': 'test',
        'integrations.zoom.client_id': 'test',
        'integrations.zoom.client_secret': 'test',
        'integrations.zoom.phone_enabled': True
    }
    zoom = ZoomIntegration(zoom_config)
    
    # Should return None when disabled
    status = zoom.get_phone_user_status('test_user')
    assert status is None, "Should return None when integration is disabled"
    
    # Test Active Directory - get_user_groups implementation
    ad_config = {
        'integrations.active_directory.enabled': False,
        'integrations.active_directory.server': 'ldap://test.local',
        'integrations.active_directory.base_dn': 'DC=test,DC=local'
    }
    ad = ActiveDirectoryIntegration(ad_config)
    
    # Should return empty list when disabled
    groups = ad.get_user_groups('testuser')
    assert groups == [], "Should return empty list when integration is disabled"
    
    # Test Active Directory - get_user_photo implementation
    photo = ad.get_user_photo('testuser')
    assert photo is None, "Should return None when integration is disabled"
    
    # Test Outlook - log_call_to_calendar implementation
    outlook_config = {
        'integrations.outlook.enabled': False,
        'integrations.outlook.tenant_id': 'test',
        'integrations.outlook.client_id': 'test',
        'integrations.outlook.client_secret': 'test'
    }
    outlook = OutlookIntegration(outlook_config)
    
    call_details = {
        'from': '555-1234',
        'to': '555-5678',
        'duration': 120,
        'direction': 'inbound',
        'timestamp': '2024-01-15T10:00:00Z'
    }
    
    # Should return False when disabled
    result = outlook.log_call_to_calendar('test@example.com', call_details)
    assert result is False, "Should return False when integration is disabled"
    
    # Test Teams - send_chat_message implementation
    teams_config = {
        'integrations.teams.enabled': False,
        'integrations.microsoft_teams.tenant_id': 'test',
        'integrations.microsoft_teams.client_id': 'test',
        'integrations.microsoft_teams.client_secret': 'test'
    }
    teams = TeamsIntegration(teams_config)
    
    # Should return False when disabled
    result = teams.send_chat_message('test@example.com', 'Hello from PBX')
    assert result is False, "Should return False when integration is disabled"
    
    # Test Active Directory - sync_users implementation
    sync_result = ad.sync_users()
    assert sync_result == 0, "Should return 0 when integration is disabled or auto_provision is off"
    
    print("✓ New integration implementations work correctly")


def test_database_backend():
    """Test database backend with SQLite"""
    print("Testing database backend...")
    
    from pbx.utils.database import DatabaseBackend, VIPCallerDB
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        
        config = {
            'database.type': 'sqlite',
            'database.path': db_path
        }
        
        # Test database connection
        db = DatabaseBackend(config)
        assert db.connect()
        assert db.enabled
        
        # Test table creation
        assert db.create_tables()
        
        # Test VIP caller operations
        vip_db = VIPCallerDB(db)
        
        # Add VIP
        assert vip_db.add_vip('5551234', priority_level=1, name='Test VIP', notes='Test notes')
        
        # Check if VIP
        assert vip_db.is_vip('5551234')
        assert not vip_db.is_vip('5559999')
        
        # Get VIP
        vip = vip_db.get_vip('5551234')
        assert vip is not None
        assert vip['name'] == 'Test VIP'
        assert vip['priority_level'] == 1
        
        # List VIPs
        vips = vip_db.list_vips()
        assert len(vips) == 1
        assert vips[0]['caller_id'] == '5551234'
        
        # Update VIP
        assert vip_db.add_vip('5551234', priority_level=2, name='Updated VIP')
        vip = vip_db.get_vip('5551234')
        assert vip['priority_level'] == 2
        assert vip['name'] == 'Updated VIP'
        
        # Remove VIP
        assert vip_db.remove_vip('5551234')
        assert not vip_db.is_vip('5551234')
        
        # Disconnect
        db.disconnect()
        assert not db.enabled
        
    print("✓ Database backend works")


def test_ad_group_permissions_mapping():
    """Test Active Directory group-based permissions mapping"""
    print("Testing AD group permissions mapping...")
    
    from pbx.integrations.active_directory import ActiveDirectoryIntegration
    
    # Test configuration with group permissions
    ad_config = {
        'integrations.active_directory.enabled': False,  # Disabled for unit test
        'integrations.active_directory.server': 'ldap://test.local',
        'integrations.active_directory.base_dn': 'DC=test,DC=local',
        'integrations.active_directory.group_permissions': {
            'CN=PBX_Admins,OU=Groups,DC=test,DC=local': ['admin', 'manage_extensions', 'view_cdr'],
            'CN=Sales,OU=Groups,DC=test,DC=local': ['external_calling', 'international_calling'],
            'CN=Support,OU=Groups,DC=test,DC=local': ['call_recording', 'call_queues'],
            'CN=Executives,OU=Groups,DC=test,DC=local': ['vip_status', 'priority_routing'],
        }
    }
    
    ad = ActiveDirectoryIntegration(ad_config)
    
    # Test case 1: User in admin group
    user_groups = ['CN=PBX_Admins,OU=Groups,DC=test,DC=local', 'CN=Domain Users,OU=Groups,DC=test,DC=local']
    permissions = ad._map_groups_to_permissions(user_groups)
    assert permissions.get('admin') == True, "Admin permission should be granted"
    assert permissions.get('manage_extensions') == True, "Manage extensions permission should be granted"
    assert permissions.get('view_cdr') == True, "View CDR permission should be granted"
    assert 'external_calling' not in permissions, "External calling should not be granted"
    
    # Test case 2: User in multiple groups
    user_groups = ['CN=Sales,OU=Groups,DC=test,DC=local', 'CN=Support,OU=Groups,DC=test,DC=local']
    permissions = ad._map_groups_to_permissions(user_groups)
    assert permissions.get('external_calling') == True, "External calling should be granted"
    assert permissions.get('international_calling') == True, "International calling should be granted"
    assert permissions.get('call_recording') == True, "Call recording should be granted"
    assert permissions.get('call_queues') == True, "Call queues should be granted"
    assert 'admin' not in permissions, "Admin permission should not be granted"
    
    # Test case 3: User with no matching groups
    user_groups = ['CN=HR,OU=Groups,DC=test,DC=local', 'CN=Finance,OU=Groups,DC=test,DC=local']
    permissions = ad._map_groups_to_permissions(user_groups)
    assert len(permissions) == 0, "No permissions should be granted for non-configured groups"
    
    # Test case 4: User with CN-only group names (short format)
    user_groups = ['Sales', 'Executives']  # Short format without full DN
    permissions = ad._map_groups_to_permissions(user_groups)
    assert permissions.get('external_calling') == True, "Should match by CN short name"
    assert permissions.get('vip_status') == True, "Should match by CN short name"
    
    # Test case 5: Empty group list
    user_groups = []
    permissions = ad._map_groups_to_permissions(user_groups)
    assert len(permissions) == 0, "No permissions for empty group list"
    
    # Test case 6: No group permissions configured
    ad_no_perms = ActiveDirectoryIntegration({
        'integrations.active_directory.enabled': False,
        'integrations.active_directory.server': 'ldap://test.local',
        'integrations.active_directory.base_dn': 'DC=test,DC=local'
    })
    user_groups = ['CN=Sales,OU=Groups,DC=test,DC=local']
    permissions = ad_no_perms._map_groups_to_permissions(user_groups)
    assert len(permissions) == 0, "No permissions when group_permissions not configured"
    
    print("✓ AD group permissions mapping works correctly")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running Stub Implementation Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_vip_caller_database,
        test_dtmf_detection,
        test_voicemail_ivr,
        test_operator_console_features,
        test_integration_stubs,
        test_new_integration_implementations,
        test_database_backend,
        test_ad_group_permissions_mapping,
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
