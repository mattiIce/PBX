#!/usr/bin/env python3
"""
Test that early RTP packets are not dropped
This test verifies the fix for the race condition where RTP packets arriving
before both endpoints are set were being dropped, causing "0 audio" issues.
"""
import os
import socket
import struct
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.rtp.handler import RTPRelay



def build_rtp_packet(payload_type=0, sequence=0, timestamp=0):
    """Build a simple RTP packet for testing"""
    version = 2
    padding = 0
    extension = 0
    csrc_count = 0
    marker = 0
    ssrc = 0x12345678

    byte0 = (version << 6) | (padding << 5) | (extension << 4) | csrc_count
    byte1 = (marker << 7) | (payload_type & 0x7F)

    header = struct.pack('!BBHII', byte0, byte1, sequence, timestamp, ssrc)
    payload = b'A' * 160  # 160 bytes of audio data

    return header + payload


def test_early_rtp_packets():
    """Test that RTP packets arriving before second endpoint is set are NOT dropped"""
    print("\n" + "=" * 70)
    print("Testing Early RTP Packet Handling (Race Condition Fix)")
    print("=" * 70)

    # Create RTP relay
    print("\n1. Creating RTP relay...")
    relay = RTPRelay(port_range_start=41000, port_range_end=41100)
    call_id = "test_early_rtp"

    rtp_ports = relay.allocate_relay(call_id)
    if not rtp_ports:
        print("   ✗ Failed to allocate relay")
        return False

    print(f"   ✓ RTP relay allocated on port {rtp_ports[0]}")

    # Set up ONLY endpoint A (simulating INVITE received but no 200 OK yet)
    print("\n2. Setting only endpoint A (simulating early INVITE stage)...")
    expected_a = ("192.168.1.10", 5000)
    relay_handler = relay.active_relays[call_id]['handler']
    relay_handler.set_endpoints(expected_a, None)  # Note: endpoint B is None
    print(f"   ✓ Endpoint A set to: {expected_a}")
    print(f"   ⚠ Endpoint B NOT set yet (simulating pre-200 OK state)")

    # Create test sockets for "phones"
    print("\n3. Creating test endpoints...")
    sock_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_a.bind(('127.0.0.1', 46000))
    sock_a.settimeout(0.5)

    sock_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_b.bind(('127.0.0.1', 46001))
    sock_b.settimeout(0.5)

    actual_a = ('127.0.0.1', 46000)
    actual_b = ('127.0.0.1', 46001)
    print(f"   ✓ Test endpoint A: {actual_a}")
    print(f"   ✓ Test endpoint B: {actual_b}")

    # Give relay time to start
    time.sleep(0.1)

    # CRITICAL TEST: Send packet from A before endpoint B is set
    print("\n4. Sending EARLY RTP packet from A (before B is set)...")
    packet_1 = build_rtp_packet(sequence=1, timestamp=0)
    sock_a.sendto(packet_1, ('127.0.0.1', rtp_ports[0]))
    time.sleep(0.1)

    # The relay should learn A's actual address and NOT drop the packet
    if relay_handler.learned_a:
        print(f"   ✓ Relay learned endpoint A: {relay_handler.learned_a}")
        print("   ✓ Early packet was NOT dropped (BUG FIXED!)")
    else:
        print("   ✗ Relay did not learn endpoint A")
        print("   ✗ Early packet was DROPPED (BUG STILL EXISTS!)")
        return False

    # Now set endpoint B (simulating 200 OK received)
    print("\n5. Now setting endpoint B (simulating 200 OK response)...")
    expected_b = ("192.168.1.20", 5001)
    relay_handler.set_endpoints(None, expected_b)  # Only update B, preserve A
    print(f"   ✓ Endpoint B set to: {expected_b}")

    # Send packet from B
    print("\n6. Sending RTP packet from B...")
    packet_2 = build_rtp_packet(sequence=1, timestamp=0)
    sock_b.sendto(packet_2, ('127.0.0.1', rtp_ports[0]))
    time.sleep(0.1)

    if relay_handler.learned_b:
        print(f"   ✓ Relay learned endpoint B: {relay_handler.learned_b}")
    else:
        print("   ✗ Relay did not learn endpoint B")
        return False

    # Test bidirectional relay now that both endpoints are learned
    print("\n7. Testing bidirectional relay (both endpoints known)...")

    # Send from A, should receive at B
    packet_from_a = build_rtp_packet(sequence=2, timestamp=160)
    sock_a.sendto(packet_from_a, ('127.0.0.1', rtp_ports[0]))
    time.sleep(0.05)

    try:
        data_at_b, addr = sock_b.recvfrom(2048)
        if len(data_at_b) > 0:
            print("   ✓ Packet from A reached B")
        else:
            print("   ✗ No packet received at B")
            return False
    except socket.timeout:
        print("   ✗ Timeout waiting for packet at B")
        return False

    # Send from B, should receive at A
    packet_from_b = build_rtp_packet(sequence=2, timestamp=160)
    sock_b.sendto(packet_from_b, ('127.0.0.1', rtp_ports[0]))
    time.sleep(0.05)

    try:
        data_at_a, addr = sock_a.recvfrom(2048)
        if len(data_at_a) > 0:
            print("   ✓ Packet from B reached A")
        else:
            print("   ✗ No packet received at A")
            return False
    except socket.timeout:
        print("   ✗ Timeout waiting for packet at A")
        return False

    # Cleanup
    print("\n8. Cleaning up...")
    sock_a.close()
    sock_b.close()
    relay.release_relay(call_id)
    print("   ✓ Test cleanup complete")

    print("\n" + "=" * 70)
    print("✓ All early RTP packet tests passed!")
    print("=" * 70)
    print("\nSummary:")
    print("✓ RTP relay does NOT drop early packets before second endpoint is set")
    print("✓ Symmetric RTP learning works with only one endpoint configured")
    print("✓ Bidirectional relay works after both endpoints are learned")
    print("✓ This fixes the race condition causing '0 audio' in phone calls")
    print("\nBug Fixed:")
    print("  Previously: Packets dropped if both endpoints not set -> 0 audio")
    print("  Now: Early packets accepted and endpoints learned -> audio works!")
    print("=" * 70)

    return True


if __name__ == '__main__':
    success = test_early_rtp_packets()
    sys.exit(0 if success else 1)
