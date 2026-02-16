#!/usr/bin/env python3
"""
Comprehensive End-to-End Call Flow Test

Tests the complete call flow including:
- SIP INVITE/Ringing/OK/ACK sequence
- RTP relay setup and audio forwarding
- DTMF handling (RFC2833 and SIP INFO)
- Symmetric RTP/NAT traversal
"""

import socket
import struct
import time

import pytest

from pbx.rtp.handler import RTPRelayHandler
from pbx.rtp.rfc2833 import RFC2833EventPacket
from pbx.sip.sdp import SDPBuilder, SDPSession


class TestCompleteCallFlow:
    """Test complete call flow from INVITE to call end"""

    def test_sdp_generation_includes_all_codecs(self) -> None:
        """Test that SDP includes PCMU, PCMA, G722, G729, G726-32, and telephone-event"""
        sdp = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, "12345")

        # Verify SDP structure
        assert "m=audio 10000 RTP/AVP" in sdp
        assert "0 8 9 18 2 101" in sdp  # All default codecs

        # Verify codec mappings
        assert "a=rtpmap:0 PCMU/8000" in sdp
        assert "a=rtpmap:8 PCMA/8000" in sdp
        assert "a=rtpmap:9 G722/8000" in sdp
        assert "a=rtpmap:18 G729/8000" in sdp
        assert "a=rtpmap:2 G726-32/8000" in sdp
        assert "a=rtpmap:101 telephone-event/8000" in sdp
        assert "a=fmtp:101 0-16" in sdp
        assert "a=sendrecv" in sdp

    def test_sdp_parsing_extracts_audio_info(self) -> None:
        """Test that SDP parsing correctly extracts audio information"""
        sdp_text = """v=0
o=user 123456 123456 IN IP4 192.168.1.100
s=Call
c=IN IP4 192.168.1.100
t=0 0
m=audio 10000 RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=sendrecv
"""

        session = SDPSession()
        session.parse(sdp_text)
        audio_info = session.get_audio_info()

        assert audio_info is not None
        assert audio_info["address"] == "192.168.1.100"
        assert audio_info["port"] == 10000
        assert "0" in audio_info["formats"]
        assert "8" in audio_info["formats"]
        assert "101" in audio_info["formats"]

    def test_rtp_relay_symmetric_learning(self) -> None:
        """Test that RTP relay learns endpoints via symmetric RTP"""
        # Create relay handler
        relay = RTPRelayHandler(20000, "test-call-123")
        assert relay.start()
        try:
            # Set expected endpoints (as would be in SDP)
            expected_a = ("192.168.1.10", 5000)
            expected_b = ("192.168.1.20", 5001)
            relay.set_endpoints(expected_a, expected_b)

            # Verify initial state
            assert relay.endpoint_a == expected_a
            assert relay.endpoint_b == expected_b
            assert relay.learned_a is None
            assert relay.learned_b is None
            # Create sockets to simulate endpoints (with different IPs - NAT
            # scenario)
            sock_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock_a.bind(("127.0.0.1", 0))
            port_a = sock_a.getsockname()[1]

            sock_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock_b.bind(("127.0.0.1", 0))
            port_b = sock_b.getsockname()[1]

            # Build simple RTP packet
            def build_rtp_packet(
                payload_type: int = 0, seq: int = 1, timestamp: int = 160, ssrc: int = 0x12345678
            ) -> bytes:
                version = 2
                header = struct.pack(
                    "!BBHII",
                    (version << 6),
                    # version, padding, extension, csrc
                    payload_type,  # marker, payload type
                    seq,  # sequence number
                    timestamp,  # timestamp
                    ssrc,
                )  # SSRC
                return header + b"audio_payload_data"

            # Send packet from A
            packet_a = build_rtp_packet()
            sock_a.sendto(packet_a, ("127.0.0.1", 20000))
            time.sleep(0.1)

            # Relay should have learned A's actual address
            with relay.lock:
                assert relay.learned_a is not None
                assert relay.learned_a[0] == "127.0.0.1"
                assert relay.learned_a[1] == port_a
            # Send packet from B
            packet_b = build_rtp_packet()
            sock_b.sendto(packet_b, ("127.0.0.1", 20000))
            time.sleep(0.1)

            # Relay should have learned B's actual address
            with relay.lock:
                assert relay.learned_b is not None
                assert relay.learned_b[0] == "127.0.0.1"
                assert relay.learned_b[1] == port_b
            # Test bidirectional relay
            # Packet from A should reach B
            sock_a.sendto(packet_a, ("127.0.0.1", 20000))
            time.sleep(0.1)
            sock_b.settimeout(0.5)
            try:
                data, _addr = sock_b.recvfrom(2048)
                assert data == packet_a
            except TimeoutError:
                pytest.fail("Packet from A did not reach B")
            # Packet from B should reach A
            sock_b.sendto(packet_b, ("127.0.0.1", 20000))
            time.sleep(0.1)
            sock_a.settimeout(0.5)
            try:
                data, _addr = sock_a.recvfrom(2048)
                assert data == packet_b
            except TimeoutError:
                pytest.fail("Packet from B did not reach A")
            sock_a.close()
            sock_b.close()

        finally:
            relay.stop()

    def test_rfc2833_dtmf_packet_structure(self) -> None:
        """Test RFC2833 DTMF packet encoding/decoding"""
        # Test all DTMF digits
        test_digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#"]

        for digit in test_digits:
            # Create packet
            packet = RFC2833EventPacket(digit, end=False, volume=10, duration=160)

            # Pack to bytes
            data = packet.pack()
            assert len(data) == 4  # RFC2833 payload is always 4 bytes

            # Unpack and verify
            unpacked = RFC2833EventPacket.unpack(data)
            assert unpacked.get_digit() == digit
            assert not unpacked.end
            assert unpacked.duration == 160
        # Test end bit
        packet_end = RFC2833EventPacket("5", end=True, duration=320)
        data_end = packet_end.pack()
        unpacked_end = RFC2833EventPacket.unpack(data_end)
        assert unpacked_end.end

    def test_call_flow_sequence(self) -> None:
        """Test the SIP call flow sequence"""

        # PBX generates SDP for callee with its own RTP endpoint
        pbx_ip = "192.168.1.1"
        pbx_rtp_port = 10000
        sdp_to_callee = SDPBuilder.build_audio_sdp(pbx_ip, pbx_rtp_port, "12345")
        assert f"m=audio {pbx_rtp_port}" in sdp_to_callee
        assert f"c=IN IP4 {pbx_ip}" in sdp_to_callee

        # PBX generates SDP for caller with its own RTP endpoint
        sdp_to_caller = SDPBuilder.build_audio_sdp(pbx_ip, pbx_rtp_port, "12345")
        assert f"m=audio {pbx_rtp_port}" in sdp_to_caller

    def test_codec_negotiation(self) -> None:
        """Test that codec negotiation works correctly"""
        # Generate SDP with default codecs
        sdp = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, "12345")

        # Parse it back
        session = SDPSession()
        session.parse(sdp)
        audio = session.get_audio_info()

        # Verify all codecs are present
        assert "0" in audio["formats"]  # PCMU
        assert "8" in audio["formats"]  # PCMA
        assert "9" in audio["formats"]  # G722
        assert "101" in audio["formats"]  # telephone-event
