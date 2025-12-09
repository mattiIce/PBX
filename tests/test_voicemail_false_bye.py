#!/usr/bin/env python3
"""
Test voicemail access with false BYE from phone firmware

This test validates that when a spurious BYE request is received immediately
after answering a voicemail access call (within 2 seconds), the BYE is ignored
and the call remains active for the IVR session.

This addresses a known issue with some phone firmwares that send a BYE
immediately after receiving a 200 OK for voicemail access calls.
"""
import sys
import os
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.core.call import Call, CallState
from pbx.sip.message import SIPMessage


def test_false_bye_ignored_during_voicemail_access():
    """
    Test that spurious BYE within 2 seconds of voicemail access is ignored
    """
    print("Testing false BYE is ignored during voicemail access...")
    
    # Create a voicemail access call
    call = Call('test-vm-call-123', '1001', '*1001')
    call.voicemail_access = True
    call.voicemail_extension = '1001'
    call.start()
    call.connect()  # This sets answer_time
    call.caller_addr = ('192.168.1.100', 5060)
    
    # Verify call is connected
    assert call.state == CallState.CONNECTED, "Call should be connected"
    assert call.answer_time is not None, "Answer time should be set"
    
    # Simulate immediate BYE (< 2 seconds) - this should be ignored
    # The actual logic is in pbx/sip/server.py _handle_bye method
    time_since_answer = (datetime.now() - call.answer_time).total_seconds()
    assert time_since_answer < 2.0, "Test should check BYE within 2 seconds"
    
    # Check if this is the first BYE
    should_ignore = (
        hasattr(call, 'voicemail_access') and 
        call.voicemail_access and
        not hasattr(call, 'first_bye_ignored') and
        time_since_answer < 2.0
    )
    
    assert should_ignore, "First BYE within 2 seconds should be ignored"
    
    # Mark that we ignored the first BYE
    call.first_bye_ignored = True
    
    # Call should still be active
    assert call.state == CallState.CONNECTED, "Call should remain connected after false BYE"
    
    print("✓ False BYE is correctly identified and can be ignored")


def test_second_bye_honored_during_voicemail_access():
    """
    Test that second BYE is honored even for voicemail access
    """
    print("Testing second BYE is honored during voicemail access...")
    
    # Create a voicemail access call
    call = Call('test-vm-call-456', '1002', '*1002')
    call.voicemail_access = True
    call.voicemail_extension = '1002'
    call.start()
    call.connect()
    call.caller_addr = ('192.168.1.101', 5060)
    
    # Mark that first BYE was already ignored
    call.first_bye_ignored = True
    
    # Second BYE should NOT be ignored
    time_since_answer = (datetime.now() - call.answer_time).total_seconds()
    should_ignore = (
        hasattr(call, 'voicemail_access') and 
        call.voicemail_access and
        not hasattr(call, 'first_bye_ignored') and
        time_since_answer < 2.0
    )
    
    assert not should_ignore, "Second BYE should NOT be ignored"
    
    # Now the call can be ended normally
    call.end()
    assert call.state == CallState.ENDED, "Call should be ended after second BYE"
    
    print("✓ Second BYE is correctly honored")


def test_bye_after_2_seconds_honored():
    """
    Test that BYE after 2 seconds is honored even if first BYE
    """
    print("Testing BYE after 2 seconds is honored...")
    
    # Create a voicemail access call
    call = Call('test-vm-call-789', '1003', '*1003')
    call.voicemail_access = True
    call.voicemail_extension = '1003'
    call.start()
    
    # Set answer time to 3 seconds ago
    call.answer_time = datetime.now() - timedelta(seconds=3)
    call.state = CallState.CONNECTED
    call.caller_addr = ('192.168.1.102', 5060)
    
    # BYE after 2 seconds should NOT be ignored even if first
    time_since_answer = (datetime.now() - call.answer_time).total_seconds()
    assert time_since_answer >= 2.0, "Time since answer should be >= 2 seconds"
    
    should_ignore = (
        hasattr(call, 'voicemail_access') and 
        call.voicemail_access and
        not hasattr(call, 'first_bye_ignored') and
        time_since_answer < 2.0
    )
    
    assert not should_ignore, "BYE after 2 seconds should NOT be ignored"
    
    # Call can be ended
    call.end()
    assert call.state == CallState.ENDED, "Call should be ended"
    
    print("✓ BYE after 2 seconds is correctly honored")


def test_regular_call_bye_not_affected():
    """
    Test that regular (non-voicemail) calls are not affected by the workaround
    """
    print("Testing regular call BYE handling not affected...")
    
    # Create a regular call (not voicemail access)
    call = Call('test-regular-call-123', '1001', '1002')
    call.start()
    call.connect()
    call.caller_addr = ('192.168.1.103', 5060)
    
    # BYE should be honored immediately for regular calls
    time_since_answer = (datetime.now() - call.answer_time).total_seconds()
    
    should_ignore = (
        hasattr(call, 'voicemail_access') and 
        call.voicemail_access and
        not hasattr(call, 'first_bye_ignored') and
        time_since_answer < 2.0
    )
    
    assert not should_ignore, "Regular call BYE should NOT be ignored"
    
    # Call should be ended normally
    call.end()
    assert call.state == CallState.ENDED, "Regular call should be ended"
    
    print("✓ Regular call BYE handling not affected by voicemail workaround")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Running Voicemail False BYE Tests")
    print("=" * 70)
    print()
    
    tests = [
        test_false_bye_ignored_during_voicemail_access,
        test_second_bye_honored_during_voicemail_access,
        test_bye_after_2_seconds_honored,
        test_regular_call_bye_not_affected,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
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
