#!/usr/bin/env python3
"""
QoS Fix Verification Script

This script verifies that the QoS sampling bug has been fixed.
Run this AFTER restarting the PBX to confirm the fix is active.

Usage:
    python scripts/verify_qos_fix.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from pbx.features.qos_monitoring import QoSMetrics


def verify_fix() -> int:
    """Verify the QoS sampling fix is working correctly"""

    print("=" * 70)
    print("QoS FIX VERIFICATION TEST")
    print("=" * 70)
    print()

    # Test: Simulate receiving 100 consecutive packets (no gaps)
    # Before fix: Sampling every 10th would cause 90% false packet loss
    # After fix: Should show 0% packet loss

    print("Test: Receiving 100 consecutive RTP packets (sequence 1000-1099)")
    print("-" * 70)

    metrics = QoSMetrics("test-verification-call")

    # Simulate receiving 100 consecutive packets
    for seq in range(1000, 1100):
        metrics.update_packet_received(seq, seq * 160, 160)

    # End the call
    metrics.end_call()

    # Get summary
    summary = metrics.get_summary()

    print(f"Packets received: {summary['packets_received']}")
    print(f"Packets lost: {summary['packets_lost']}")
    print(f"Packet loss %: {summary['packet_loss_percentage']}%")
    print(f"MOS Score: {summary['mos_score']}")
    print(f"Quality Rating: {summary['quality_rating']}")
    print()

    # Verify results
    passed = True

    print("VERIFICATION RESULTS:")
    print("-" * 70)

    # Check 1: All packets should be counted
    if summary["packets_received"] == 100:
        print("✅ PASS: All 100 packets were counted")
    else:
        print(f"❌ FAIL: Expected 100 packets, got {summary['packets_received']}")
        passed = False

    # Check 2: No packet loss should be detected
    if summary["packets_lost"] == 0:
        print("✅ PASS: No packet loss detected")
    else:
        print(f"❌ FAIL: Detected {summary['packets_lost']} lost packets (should be 0)")
        passed = False

    # Check 3: Packet loss percentage should be 0%
    if summary["packet_loss_percentage"] == 0.0:
        print("✅ PASS: Packet loss percentage is 0%")
    else:
        print(f"❌ FAIL: Packet loss is {summary['packet_loss_percentage']}% (should be 0%)")
        passed = False

    # Check 4: MOS score should be good (>= 4.0)
    if summary["mos_score"] >= 4.0:
        print(f"✅ PASS: MOS score is good ({summary['mos_score']})")
    else:
        print(f"❌ FAIL: MOS score is {summary['mos_score']} (should be >= 4.0)")
        passed = False

    print()

    if passed:
        print("=" * 70)
        print("🎉 ALL TESTS PASSED - QoS FIX IS WORKING CORRECTLY!")
        print("=" * 70)
        print()
        print("You can now make test calls and expect:")
        print("  - Accurate packet loss percentages (not 90%)")
        print("  - Correct MOS scores for call quality")
        print("  - Proper jitter calculations")
        print()
        return 0
    print("=" * 70)
    print("❌ TESTS FAILED - QoS FIX NOT WORKING")
    print("=" * 70)
    print()
    print("Possible causes:")
    print("  1. PBX was not restarted after applying the fix")
    print("  2. Code changes were not properly saved")
    print("  3. Running old cached Python bytecode (.pyc files)")
    print()
    print("Try:")
    print("  1. Restart the PBX service")
    print("  2. Delete .pyc files: find . -name '*.pyc' -delete")
    print("  3. Run this verification script again")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(verify_fix())
