#!/usr/bin/env python3
"""
Test WebRTC browser calling support
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.webrtc import WebRTCSignalingServer, WebRTCSession, WebRTCGateway


def test_webrtc_session_creation():
    """Test WebRTC session creation"""
    print("Testing WebRTC session creation...")
    
    session = WebRTCSession(
        session_id='test-session-123',
        extension='1001'
    )
    
    assert session.session_id == 'test-session-123', "Session ID should match"
    assert session.extension == '1001', "Extension should match"
    assert session.state == 'new', "Initial state should be 'new'"
    assert session.peer_connection_id is not None, "Peer connection ID should be set"
    
    # Test to_dict()
    session_dict = session.to_dict()
    assert 'session_id' in session_dict, "Should have session_id"
    assert 'extension' in session_dict, "Should have extension"
    assert 'state' in session_dict, "Should have state"
    
    print("✓ WebRTC session creation works")
    return True


def test_webrtc_signaling_initialization():
    """Test WebRTC signaling server initialization"""
    print("\nTesting WebRTC signaling server initialization...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.webrtc.enabled': True,
                'features.webrtc.session_timeout': 300,
                'features.webrtc.stun_servers': [
                    'stun:stun.l.google.com:19302'
                ],
                'features.webrtc.turn_servers': [],
                'features.webrtc.ice_transport_policy': 'all'
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    signaling = WebRTCSignalingServer(config)
    
    assert signaling.enabled == True, "Should be enabled"
    assert signaling.session_timeout == 300, "Session timeout should be 300"
    assert len(signaling.stun_servers) == 1, "Should have 1 STUN server"
    assert signaling.ice_transport_policy == 'all', "ICE policy should be 'all'"
    
    signaling.stop()
    
    print("✓ WebRTC signaling server initialization works")
    return True


def test_webrtc_session_management():
    """Test WebRTC session management"""
    print("\nTesting WebRTC session management...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.webrtc.enabled': True,
                'features.webrtc.session_timeout': 300
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    signaling = WebRTCSignalingServer(config)
    
    # Create session
    session = signaling.create_session('1001')
    assert session is not None, "Session should be created"
    assert session.extension == '1001', "Extension should match"
    
    # Get session
    retrieved_session = signaling.get_session(session.session_id)
    assert retrieved_session is not None, "Should retrieve session"
    assert retrieved_session.session_id == session.session_id, "Session ID should match"
    
    # Get sessions by extension
    ext_sessions = signaling.get_extension_sessions('1001')
    assert len(ext_sessions) == 1, "Should have 1 session for extension"
    assert ext_sessions[0].session_id == session.session_id, "Session should match"
    
    # Close session
    success = signaling.close_session(session.session_id)
    assert success == True, "Should close successfully"
    
    # Verify session is removed
    retrieved_session = signaling.get_session(session.session_id)
    assert retrieved_session is None, "Session should be removed"
    
    signaling.stop()
    
    print("✓ WebRTC session management works")
    return True


def test_webrtc_sdp_handling():
    """Test WebRTC SDP offer/answer handling"""
    print("\nTesting WebRTC SDP offer/answer handling...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.webrtc.enabled': True
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    signaling = WebRTCSignalingServer(config)
    
    # Create session
    session = signaling.create_session('1002')
    
    # Test SDP offer
    test_sdp_offer = "v=0\r\no=- 123456789 2 IN IP4 192.168.1.1\r\n..."
    success = signaling.handle_offer(session.session_id, test_sdp_offer)
    assert success == True, "Should handle offer"
    
    retrieved_session = signaling.get_session(session.session_id)
    assert retrieved_session.local_sdp == test_sdp_offer, "SDP should be stored"
    assert retrieved_session.state == 'connecting', "State should be 'connecting'"
    
    # Test SDP answer
    test_sdp_answer = "v=0\r\no=- 987654321 2 IN IP4 192.168.1.2\r\n..."
    success = signaling.handle_answer(session.session_id, test_sdp_answer)
    assert success == True, "Should handle answer"
    
    retrieved_session = signaling.get_session(session.session_id)
    assert retrieved_session.remote_sdp == test_sdp_answer, "SDP should be stored"
    assert retrieved_session.state == 'connected', "State should be 'connected'"
    
    signaling.stop()
    
    print("✓ WebRTC SDP offer/answer handling works")
    return True


def test_webrtc_ice_candidates():
    """Test WebRTC ICE candidate handling"""
    print("\nTesting WebRTC ICE candidate handling...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.webrtc.enabled': True
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    signaling = WebRTCSignalingServer(config)
    
    # Create session
    session = signaling.create_session('1003')
    
    # Add ICE candidate
    test_candidate = {
        'candidate': 'candidate:1 1 UDP 2130706431 192.168.1.1 54321 typ host',
        'sdpMid': 'audio',
        'sdpMLineIndex': 0
    }
    success = signaling.add_ice_candidate(session.session_id, test_candidate)
    assert success == True, "Should add ICE candidate"
    
    retrieved_session = signaling.get_session(session.session_id)
    assert len(retrieved_session.ice_candidates) == 1, "Should have 1 ICE candidate"
    assert retrieved_session.ice_candidates[0] == test_candidate, "Candidate should match"
    
    signaling.stop()
    
    print("✓ WebRTC ICE candidate handling works")
    return True


def test_webrtc_ice_servers_config():
    """Test ICE servers configuration"""
    print("\nTesting ICE servers configuration...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.webrtc.enabled': True,
                'features.webrtc.stun_servers': [
                    'stun:stun.l.google.com:19302',
                    'stun:stun1.l.google.com:19302'
                ],
                'features.webrtc.turn_servers': [
                    {
                        'url': 'turn:turn.example.com:3478',
                        'username': 'user1',
                        'credential': 'pass1'
                    }
                ],
                'features.webrtc.ice_transport_policy': 'all'
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    signaling = WebRTCSignalingServer(config)
    
    ice_config = signaling.get_ice_servers_config()
    
    assert 'iceServers' in ice_config, "Should have iceServers"
    assert 'iceTransportPolicy' in ice_config, "Should have iceTransportPolicy"
    assert ice_config['iceTransportPolicy'] == 'all', "ICE policy should be 'all'"
    assert len(ice_config['iceServers']) == 3, "Should have 3 ICE servers (2 STUN + 1 TURN)"
    
    signaling.stop()
    
    print("✓ ICE servers configuration works")
    return True


def test_webrtc_gateway():
    """Test WebRTC gateway"""
    print("\nTesting WebRTC gateway...")
    
    gateway = WebRTCGateway()
    
    # Test SDP conversion (simplified)
    test_sdp = "v=0\r\no=- 123456789 2 IN IP4 192.168.1.1\r\n..."
    
    # Test WebRTC to SIP conversion
    sip_sdp = gateway.webrtc_to_sip_sdp(test_sdp)
    assert sip_sdp is not None, "Should convert WebRTC to SIP SDP"
    
    # Test SIP to WebRTC conversion
    webrtc_sdp = gateway.sip_to_webrtc_sdp(test_sdp)
    assert webrtc_sdp is not None, "Should convert SIP to WebRTC SDP"
    
    print("✓ WebRTC gateway works")
    return True


def test_sdp_transformations():
    """Test SDP transformations between WebRTC and SIP"""
    print("\nTesting SDP transformations...")
    
    gateway = WebRTCGateway()
    
    # Sample WebRTC SDP with DTLS-SRTP
    webrtc_sdp = """v=0
o=- 123456789 2 IN IP4 192.168.1.100
s=WebRTC Call
c=IN IP4 192.168.1.100
t=0 0
m=audio 54321 UDP/TLS/RTP/SAVPF 111 0 8
a=rtpmap:111 opus/48000/2
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=ice-ufrag:abcd1234
a=ice-pwd:abcdef1234567890abcdef12
a=ice-options:trickle
a=fingerprint:sha-256 AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99
a=setup:actpass
a=mid:0
a=rtcp-mux
a=sendrecv
"""
    
    # Test WebRTC to SIP conversion
    sip_sdp = gateway.webrtc_to_sip_sdp(webrtc_sdp)
    assert 'RTP/AVP' in sip_sdp or 'RTP/SAVPF' in sip_sdp, "Should have RTP protocol"
    assert 'ice-ufrag' not in sip_sdp, "Should remove WebRTC-specific ICE attributes"
    assert 'fingerprint' not in sip_sdp, "Should remove DTLS fingerprint"
    
    # Sample SIP SDP
    sip_sdp = """v=0
o=pbx 987654321 0 IN IP4 192.168.1.10
s=PBX Call
c=IN IP4 192.168.1.10
t=0 0
m=audio 10000 RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=sendrecv
"""
    
    # Test SIP to WebRTC conversion
    webrtc_sdp = gateway.sip_to_webrtc_sdp(sip_sdp)
    assert 'RTP/SAVPF' in webrtc_sdp, "Should convert to RTP/SAVPF"
    assert 'ice-ufrag' in webrtc_sdp, "Should add ICE username fragment"
    assert 'ice-pwd' in webrtc_sdp, "Should add ICE password"
    assert 'sha-256' in webrtc_sdp, "Should add DTLS fingerprint (sha-256)"
    assert 'setup:actpass' in webrtc_sdp, "Should add DTLS setup attribute"
    assert 'rtcp-mux' in webrtc_sdp, "Should add RTCP multiplexing"
    
    print("✓ SDP transformations work correctly")
    return True


def test_call_initiation():
    """Test call initiation through WebRTC gateway"""
    print("\nTesting call initiation...")
    
    # Create mock PBX core with necessary components
    class MockExtension:
        def __init__(self, number):
            self.number = number
    
    class MockExtensionRegistry:
        def get_extension(self, number):
            if number in ['1001', '1002']:
                return MockExtension(number)
            return None
    
    class MockCallManager:
        def __init__(self):
            self.calls = {}
        
        def create_call(self, call_id, from_extension, to_extension):
            from pbx.core.call import Call
            call = Call(call_id, from_extension, to_extension)
            self.calls[call_id] = call
            return call
        
        def get_call(self, call_id):
            return self.calls.get(call_id)
    
    class MockPBXCore:
        def __init__(self):
            self.extension_registry = MockExtensionRegistry()
            self.call_manager = MockCallManager()
    
    class MockConfig:
        def get(self, key, default=None):
            return {'features.webrtc.enabled': True}.get(key, default)
    
    # Create WebRTC signaling server and gateway
    config = MockConfig()
    signaling = WebRTCSignalingServer(config)
    
    pbx_core = MockPBXCore()
    gateway = WebRTCGateway(pbx_core)
    
    # Create WebRTC session
    session = signaling.create_session('1001')
    
    # Set SDP for session
    test_sdp = """v=0
o=- 123 0 IN IP4 192.168.1.100
s=-
c=IN IP4 192.168.1.100
t=0 0
m=audio 50000 RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=sendrecv
"""
    signaling.handle_offer(session.session_id, test_sdp)
    
    # Initiate call
    call_id = gateway.initiate_call(session.session_id, '1002', signaling)
    
    assert call_id is not None, "Should return call ID"
    assert session.call_id == call_id, "Session should have call ID"
    
    # Verify call was created
    call = pbx_core.call_manager.get_call(call_id)
    assert call is not None, "Call should be created in CallManager"
    assert call.from_extension == '1001', "Call should have correct source"
    assert call.to_extension == '1002', "Call should have correct destination"
    
    signaling.stop()
    
    print("✓ Call initiation works")
    return True


def test_incoming_call_routing():
    """Test incoming call routing to WebRTC client"""
    print("\nTesting incoming call routing...")
    
    # Create mock PBX core
    class MockCallManager:
        def __init__(self):
            self.calls = {}
        
        def create_call(self, call_id, from_extension, to_extension):
            from pbx.core.call import Call
            call = Call(call_id, from_extension, to_extension)
            self.calls[call_id] = call
            return call
        
        def get_call(self, call_id):
            return self.calls.get(call_id)
    
    class MockPBXCore:
        def __init__(self):
            self.call_manager = MockCallManager()
    
    class MockConfig:
        def get(self, key, default=None):
            return {'features.webrtc.enabled': True}.get(key, default)
    
    # Create WebRTC signaling server and gateway
    config = MockConfig()
    signaling = WebRTCSignalingServer(config)
    
    pbx_core = MockPBXCore()
    gateway = WebRTCGateway(pbx_core)
    
    # Create WebRTC session
    session = signaling.create_session('1002')
    
    # Create incoming call
    call_id = 'incoming-call-123'
    call = pbx_core.call_manager.create_call(call_id, '1001', '1002')
    
    # Caller SDP
    caller_sdp = """v=0
o=pbx 456 0 IN IP4 192.168.1.10
s=-
c=IN IP4 192.168.1.10
t=0 0
m=audio 20000 RTP/AVP 0 8
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=sendrecv
"""
    
    # Route call to WebRTC client
    success = gateway.receive_call(session.session_id, call_id, caller_sdp, signaling)
    
    assert success == True, "Should route call successfully"
    assert session.call_id == call_id, "Session should have call ID"
    assert session.remote_sdp is not None, "Session should have remote SDP"
    assert 'RTP/SAVPF' in session.remote_sdp, "SDP should be converted to WebRTC format"
    
    # Verify metadata
    is_incoming = signaling.get_session_metadata(session.session_id, 'incoming_call')
    assert is_incoming == True, "Should mark as incoming call"
    
    signaling.stop()
    
    print("✓ Incoming call routing works")
    return True


def test_webrtc_disabled():
    """Test WebRTC when disabled"""
    print("\nTesting WebRTC when disabled...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.webrtc.enabled': False
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    signaling = WebRTCSignalingServer(config)
    
    assert signaling.enabled == False, "Should be disabled"
    
    # Try to create session (should raise exception)
    try:
        session = signaling.create_session('1004')
        assert False, "Should raise exception when disabled"
    except RuntimeError as e:
        assert "not enabled" in str(e).lower(), "Should have appropriate error message"
    
    print("✓ WebRTC disabled state works")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("Testing WebRTC Browser Calling Support")
    print("=" * 70)
    
    results = []
    results.append(test_webrtc_session_creation())
    results.append(test_webrtc_signaling_initialization())
    results.append(test_webrtc_session_management())
    results.append(test_webrtc_sdp_handling())
    results.append(test_webrtc_ice_candidates())
    results.append(test_webrtc_ice_servers_config())
    results.append(test_webrtc_gateway())
    results.append(test_sdp_transformations())
    results.append(test_call_initiation())
    results.append(test_incoming_call_routing())
    results.append(test_webrtc_disabled())
    
    print("\n" + "=" * 70)
    if all(results):
        print(f"✅ All WebRTC tests passed! ({len(results)}/{len(results)})")
        sys.exit(0)
    else:
        print(f"❌ Some tests failed ({sum(results)}/{len(results)} passed)")
        sys.exit(1)
