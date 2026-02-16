#!/usr/bin/env python3
"""
Test DTMF INFO handling for ended calls

This test validates that DTMF INFO messages received for calls that have
already ended are handled gracefully without producing warnings.
"""

from pbx.core.call import CallState
from pbx.core.pbx import PBXCore


def test_dtmf_info_for_ended_call_no_warning() -> None:
    """
    Test that DTMF INFO for ended calls doesn't produce warnings

    This simulates the common scenario where:
    1. Call is active
    2. BYE is received and call ends
    3. Phone sends buffered DTMF INFO messages
    4. System should handle gracefully (debug log, not warning)
    """

    # Create minimal PBX instance for testing
    pbx = PBXCore("config.yml")

    # Create and register a call
    call_id = "test-call-123"
    call = pbx.call_manager.create_call(call_id, "1001", "*1001")
    call.state = CallState.CONNECTED

    # Verify call is active
    assert pbx.call_manager.get_call(call_id) is not None

    # DTMF INFO should work for active call
    pbx.handle_dtmf_info(call_id, "1")
    assert hasattr(call, "dtmf_info_queue")
    assert "1" in call.dtmf_info_queue

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
    pbx.handle_dtmf_info(call_id, "2")
    pbx.handle_dtmf_info(call_id, "3")
    pbx.handle_dtmf_info(call_id, "4")

    # Get captured logs
    log_output = log_capture.getvalue()

    # Clean up
    logger.removeHandler(handler)
    logger.setLevel(original_level)

    # Verify that:
    # 1. The method handled the DTMF without crashing (no exceptions)
    # 2. Debug message about ended/unknown call was logged
    assert "ended/unknown call" in log_output.lower(), "Expected debug message about ended call"

    # 3. No WARNING level messages for DTMF on ended calls
    # Split log into lines and check that lines mentioning DTMF don't contain
    # WARNING
    log_lines = log_output.split("\n")
    dtmf_lines = [line for line in log_lines if "dtm" in line.lower() and "ended" in line.lower()]
    for line in dtmf_lines:
        assert "WARNING" not in line, f"Found WARNING in DTMF log line: {line}"


def test_dtmf_info_race_condition() -> None:
    """
    Test race condition where DTMF INFO arrives during call teardown
    """

    pbx = PBXCore("config.yml")

    # Create call
    call_id = "test-call-456"
    call = pbx.call_manager.create_call(call_id, "1001", "*1001")
    call.state = CallState.CONNECTED

    # Simulate rapid sequence:
    # 1. DTMF arrives
    pbx.handle_dtmf_info(call_id, "5")

    # 2. Call ends
    pbx.call_manager.end_call(call_id)

    # 3. More DTMF arrives (buffered by phone)
    pbx.handle_dtmf_info(call_id, "6")
    pbx.handle_dtmf_info(call_id, "7")

    # Should handle gracefully without exceptions
