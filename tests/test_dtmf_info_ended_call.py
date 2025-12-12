#!/usr/bin/env python3
"""
Test DTMF INFO handling for ended calls

This test validates that DTMF INFO messages received for calls that have
already ended are handled gracefully without producing warnings.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.core.call import Call, CallState
from pbx.core.pbx import PBXCore
from pbx.utils.config import Config



def test_dtmf_info_for_ended_call_no_warning():
    """
    Test that DTMF INFO for ended calls doesn't produce warnings

    This simulates the common scenario where:
    1. Call is active
    2. BYE is received and call ends
    3. Phone sends buffered DTMF INFO messages
    4. System should handle gracefully (debug log, not warning)
    """
    print("Testing DTMF INFO for ended call produces debug log (not warning)...")

    # Create minimal PBX instance for testing
    pbx = PBXCore('config.yml')

    # Create and register a call
    call_id = 'test-call-123'
    call = pbx.call_manager.create_call(call_id, '1001', '*1001')
    call.state = CallState.CONNECTED

    # Verify call is active
    assert pbx.call_manager.get_call(call_id) is not None

    # DTMF INFO should work for active call
    pbx.handle_dtmf_info(call_id, '1')
    assert hasattr(call, 'dtmf_info_queue')
    assert '1' in call.dtmf_info_queue

    # End the call (simulating BYE)
    pbx.call_manager.end_call(call_id)

    # Verify call is no longer in active calls
    assert pbx.call_manager.get_call(call_id) is None

    # Now send DTMF INFO for the ended call
    # This should not produce a WARNING, only a DEBUG message
    import logging

    from pbx.utils.logger import get_logger

    # Capture log output
    logger = get_logger()
    original_level = logger.level

    # Set to DEBUG to capture debug messages
    logger.setLevel(logging.DEBUG)

    # Create a handler to capture logs
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Send DTMF for ended call
    pbx.handle_dtmf_info(call_id, '2')
    pbx.handle_dtmf_info(call_id, '3')
    pbx.handle_dtmf_info(call_id, '4')

    # Get captured logs
    log_output = log_capture.getvalue()

    # Clean up
    logger.removeHandler(handler)
    logger.setLevel(original_level)

    # Verify that:
    # 1. The method handled the DTMF without crashing (no exceptions)
    # 2. Debug message about ended/unknown call was logged
    assert 'ended/unknown call' in log_output.lower(), "Expected debug message about ended call"

    # 3. No WARNING level messages for DTMF on ended calls
    # Split log into lines and check that lines mentioning DTMF don't contain
    # WARNING
    log_lines = log_output.split('\n')
    dtmf_lines = [line for line in log_lines if 'dtmf' in line.lower()
                  and 'ended' in line.lower()]
    for line in dtmf_lines:
        assert 'WARNING' not in line, f"Found WARNING in DTMF log line: {line}"

    print("✓ DTMF INFO for ended call handled gracefully with debug log")


def test_dtmf_info_race_condition():
    """
    Test race condition where DTMF INFO arrives during call teardown
    """
    print("Testing DTMF INFO race condition during call teardown...")

    pbx = PBXCore('config.yml')

    # Create call
    call_id = 'test-call-456'
    call = pbx.call_manager.create_call(call_id, '1001', '*1001')
    call.state = CallState.CONNECTED

    # Simulate rapid sequence:
    # 1. DTMF arrives
    pbx.handle_dtmf_info(call_id, '5')

    # 2. Call ends
    pbx.call_manager.end_call(call_id)

    # 3. More DTMF arrives (buffered by phone)
    pbx.handle_dtmf_info(call_id, '6')
    pbx.handle_dtmf_info(call_id, '7')

    # Should handle gracefully without exceptions
    print("✓ DTMF INFO race condition handled gracefully")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running DTMF INFO Ended Call Tests")
    print("=" * 60)
    print()

    tests = [
        test_dtmf_info_for_ended_call_no_warning,
        test_dtmf_info_race_condition,
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
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
