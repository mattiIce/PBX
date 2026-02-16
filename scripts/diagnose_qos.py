#!/usr/bin/env python3
"""
QoS Diagnostic Tool
Helps troubleshoot calls with poor quality or 0.0 MOS scores

Usage:
    python scripts/diagnose_qos.py [call_id]

Examples:
    python scripts/diagnose_qos.py 600703453@192.168.10.135
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def diagnose_call_quality(
    call_id: str, packets_sent: int, packets_received: int, packets_lost: int, jitter_avg: float, latency_avg: float, duration: float
) -> None:
    """
    Diagnose call quality issues

    Args:
        call_id: Call identifier
        packets_sent: Number of packets sent
        packets_received: Number of packets received
        packets_lost: Number of packets lost
        jitter_avg: Average jitter in ms
        latency_avg: Average latency in ms
        duration: Call duration in seconds
    """
    print("=" * 70)
    print(f"QoS DIAGNOSTIC REPORT FOR: {call_id}")
    print("=" * 70)
    print()

    print("CALL STATISTICS:")
    print(f"  Duration: {duration}s")
    print(f"  Packets Sent: {packets_sent}")
    print(f"  Packets Received: {packets_received}")
    print(f"  Packets Lost: {packets_lost}")
    print(f"  Average Jitter: {jitter_avg} ms")
    print(f"  Average Latency: {latency_avg} ms")
    print()

    # Calculate expected packet counts
    # Typical VoIP uses 20ms packets (50 packets/second)
    expected_packets = int(duration * 50)

    print("DIAGNOSTIC ANALYSIS:")
    print("-" * 70)

    # Issue 1: No packets received
    if packets_received == 0:
        print("❌ CRITICAL: No RTP packets received during the call")
        print("   Possible causes:")
        print("   - Firewall blocking incoming RTP packets")
        print("   - NAT traversal issues (symmetric RTP not working)")
        print("   - Endpoint not sending RTP packets")
        print("   - Wrong IP address or port in SDP")
        print("   - QoS monitoring not started for this call")
        print()

    # Issue 2: Very few packets received
    elif packets_received < expected_packets * 0.1:
        print(
            f"⚠️  WARNING: Very few packets received ({packets_received} vs expected ~{expected_packets})"
        )
        print("   Possible causes:")
        print("   - Severe network issues or packet drops")
        print("   - Call connected but one-way audio")
        print("   - QoS monitoring started late in the call")
        print()

    # Issue 3: No packets sent
    if packets_sent == 0:
        print("❌ CRITICAL: No RTP packets sent during the call")
        print("   Possible causes:")
        print("   - RTP relay not forwarding packets")
        print("   - Outbound firewall blocking RTP")
        print("   - PBX not receiving RTP from local endpoint")
        print()

    # Issue 4: Zero jitter and latency
    if jitter_avg == 0.0 and latency_avg == 0.0 and packets_received > 0:
        print("⚠️  WARNING: Jitter and latency are both 0.0 despite receiving packets")
        print("   Possible causes:")
        print("   - QoS metrics not being updated properly")
        print("   - No RTCP packets for latency measurement")
        print("   - Jitter calculation issue in code")
        print()

    # Issue 5: High packet loss
    if packets_received > 0:
        total = packets_received + packets_lost
        loss_rate = (packets_lost / total) * 100
        if loss_rate > 5:
            print(f"⚠️  WARNING: High packet loss rate: {loss_rate:.2f}%")
            print("   Possible causes:")
            print("   - Network congestion")
            print("   - Poor WiFi signal")
            print("   - Bandwidth saturation")
            print("   - QoS/traffic prioritization not configured")
            print()

    # Issue 6: High jitter
    if jitter_avg > 50:
        print(f"⚠️  WARNING: High jitter: {jitter_avg} ms")
        print("   Possible causes:")
        print("   - Variable network conditions")
        print("   - Shared bandwidth with bursty traffic")
        print("   - Need for jitter buffer tuning")
        print()

    # Issue 7: High latency
    if latency_avg > 300:
        print(f"⚠️  WARNING: High latency: {latency_avg} ms")
        print("   Possible causes:")
        print("   - Long network path (geographic distance)")
        print("   - Too many network hops")
        print("   - Slow network equipment")
        print()

    # Issue 8: MOS score is 0.0
    if packets_received == 0 and packets_sent > 0:
        print("📊 MOS SCORE: 0.0 (No Quality Data)")
        print("   Explanation:")
        print("   - MOS cannot be calculated without received packets")
        print("   - This indicates a one-way call or monitoring issue")
        print("   - Check 'No packets received' issues above")
        print()

    print("=" * 70)
    print("RECOMMENDATIONS:")
    print("-" * 70)

    if packets_received == 0:
        print("1. Check firewall rules to allow RTP port range (10000-20000)")
        print("2. Verify NAT configuration and symmetric RTP support")
        print("3. Check PBX logs for RTP relay errors")
        print("4. Use tcpdump to verify RTP packets are arriving:")
        print("   tcpdump -i any -n 'udp portrange 10000-20000'")
        print()

    if latency_avg == 0.0 and packets_received > 0:
        print("1. RTCP latency measurement is not implemented")
        print("2. This is normal - latency measurement requires RTCP support")
        print("3. MOS calculation will use jitter and packet loss only")
        print()

    print("=" * 70)


def main() -> None:
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/diagnose_qos.py <call_id>")
        print()
        print("Example from problem statement:")
        print("  python scripts/diagnose_qos.py 600703453@192.168.10.135")
        print()
        print("Or provide all metrics:")
        print(
            "  python scripts/diagnose_qos.py CALL_ID DURATION PACKETS_SENT PACKETS_RECV PACKETS_LOST JITTER LATENCY"
        )
        sys.exit(1)

    call_id = sys.argv[1]

    # Check if all metrics were provided
    if len(sys.argv) >= 8:
        duration = float(sys.argv[2])
        packets_sent = int(sys.argv[3])
        packets_received = int(sys.argv[4])
        packets_lost = int(sys.argv[5])
        jitter_avg = float(sys.argv[6])
        latency_avg = float(sys.argv[7])
    else:
        # Use the problem statement values as default
        print("Using default values from problem statement...")
        print()
        duration = 217.02
        packets_sent = 0  # Unknown from problem statement
        packets_received = 0  # Implied by 0.0 MOS
        packets_lost = 0
        jitter_avg = 0.0
        latency_avg = 0.0

    diagnose_call_quality(
        call_id, packets_sent, packets_received, packets_lost, jitter_avg, latency_avg, duration
    )


if __name__ == "__main__":
    main()
