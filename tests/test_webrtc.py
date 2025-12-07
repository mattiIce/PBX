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
    results.append(test_webrtc_disabled())
    
    print("\n" + "=" * 70)
    if all(results):
        print(f"✅ All WebRTC tests passed! ({len(results)}/{len(results)})")
        sys.exit(0)
    else:
        print(f"❌ Some tests failed ({sum(results)}/{len(results)} passed)")
        sys.exit(1)
