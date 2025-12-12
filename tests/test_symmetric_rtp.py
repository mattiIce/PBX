#!/usr/bin/env python3
"""
Test symmetric RTP support in RTP relay
This test verifies that the RTP relay can handle NAT traversal where
actual RTP source addresses differ from what's advertised in SDP.
"""
import os
import socket
import struct
import sys
import threading
import time

from pbx.rtp.handler import RTPRelay

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def test_symmetric_rtp():
    """Test that RTP relay handles NAT/different source addresses"""
    print("\n" + "=" * 60)
    print("Testing Symmetric RTP Support")
    print("=" * 60)

    # Create RTP relay
    print("\n1. Creating RTP relay...")
    relay = RTPRelay(port_range_start=40000, port_range_end=40100)
    call_id = "test_symmetric_rtp"

    rtp_ports = relay.allocate_relay(call_id)
    if not rtp_ports:
        print("   ✗ Failed to allocate relay")
        return False

    print(f"   ✓ RTP relay allocated on port {rtp_ports[0]}")

    # Set up expected endpoints (what's in SDP)
    # Simulate: Phone A advertises 192.168.1.10:5000 in SDP
    #           Phone B advertises 192.168.1.20:5001 in SDP
    print("\n2. Setting expected endpoints from SDP...")
    expected_a = ("192.168.1.10", 5000)
    expected_b = ("192.168.1.20", 5001)
    relay.set_endpoints(call_id, expected_a, expected_b)
    print(f"   ✓ Expected endpoint A: {expected_a}")
    print(f"   ✓ Expected endpoint B: {expected_b}")

    # Create test sockets for "phones"
    # But use different ports to simulate NAT
    # Actual: Phone A sends from 127.0.0.1:45000
    #         Phone B sends from 127.0.0.1:45001
    print("\n3. Creating test endpoints (simulating NAT)...")
    sock_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_a.bind(('127.0.0.1', 45000))

    sock_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_b.bind(('127.0.0.1', 45001))

    actual_a = ('127.0.0.1', 45000)
    actual_b = ('127.0.0.1', 45001)
    print(f"   ✓ Actual endpoint A: {actual_a} (different from SDP)")
    print(f"   ✓ Actual endpoint B: {actual_b} (different from SDP)")

    # Give relay time to start
    time.sleep(0.1)

    # Test: Send packet from A to relay
    print("\n4. Sending RTP packet from A to relay...")
    packet_a = build_rtp_packet(sequence=1, timestamp=0)
    sock_a.sendto(packet_a, ('127.0.0.1', rtp_ports[0]))
    time.sleep(0.1)

    # The relay should learn A's actual address
    relay_handler = relay.active_relays[call_id]['handler']
    if relay_handler.learned_a:
        print(f"   ✓ Relay learned endpoint A: {relay_handler.learned_a}")
    else:
        print("   ✗ Relay did not learn endpoint A")
        return False

    # Test: Send packet from B to relay
    print("\n5. Sending RTP packet from B to relay...")
    packet_b = build_rtp_packet(sequence=1, timestamp=0)
    sock_b.sendto(packet_b, ('127.0.0.1', rtp_ports[0]))
    time.sleep(0.1)

    # The relay should learn B's actual address
    if relay_handler.learned_b:
        print(f"   ✓ Relay learned endpoint B: {relay_handler.learned_b}")
    else:
        print("   ✗ Relay did not learn endpoint B")
        return False

    # Test: Verify packets are relayed bidirectionally
    print("\n6. Testing bidirectional relay...")

    # Set sockets to non-blocking for recv test
    sock_a.settimeout(0.5)
    sock_b.settimeout(0.5)

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
    print("\n7. Cleaning up...")
    sock_a.close()
    sock_b.close()
    relay.release_relay(call_id)
    print("   ✓ Test cleanup complete")

    print("\n" + "=" * 60)
    print("✓ All symmetric RTP tests passed!")
    print("=" * 60)
    print("\nSummary:")
    print("- RTP relay learns actual source addresses (symmetric RTP)")
    print("- Handles NAT traversal where SDP addresses differ from actual")
    print("- Packets are correctly relayed bidirectionally")
    print("- This fixes the '0 audio' issue for phone-to-phone calls")
    print("=" * 60)

    return True


if __name__ == '__main__':
    success = test_symmetric_rtp()
    sys.exit(0 if success else 1)
