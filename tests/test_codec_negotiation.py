#!/usr/bin/env python3
"""
Test codec negotiation between caller and callee
Verifies that PBX correctly negotiates codecs to prevent "488 Not Acceptable Here" errors
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.sip.sdp import SDPSession, SDPBuilder


def test_codec_extraction_from_sdp():
    """Test extracting codecs from caller's SDP"""
    print("Testing codec extraction from SDP...")
    
    # Simulate SDP from a phone with codecs: 8, 9, 0 (PCMA, G722, PCMU)
    caller_sdp_text = """v=0
o=caller 123456 654321 IN IP4 192.168.10.133
s=Phone Call
c=IN IP4 192.168.10.133
t=0 0
m=audio 10000 RTP/AVP 8 9 0
a=rtpmap:8 PCMA/8000
a=rtpmap:9 G722/8000
a=rtpmap:0 PCMU/8000
a=sendrecv
"""
    
    # Parse the SDP
    sdp = SDPSession()
    sdp.parse(caller_sdp_text)
    
    # Extract audio info
    audio_info = sdp.get_audio_info()
    
    assert audio_info is not None, "Audio info should not be None"
    assert 'formats' in audio_info, "Audio info should contain formats"
    
    # Verify the codec order is preserved
    codecs = audio_info['formats']
    assert codecs == ['8', '9', '0'], f"Expected ['8', '9', '0'], got {codecs}"
    
    print(f"  ✓ Extracted codecs: {codecs}")
    print("  ✓ Codec order preserved")


def test_sdp_building_with_caller_codecs():
    """Test building SDP with caller's codec preferences"""
    print("Testing SDP building with caller's codecs...")
    
    # Caller offered codecs: 8, 9, 0 (PCMA, G722, PCMU)
    caller_codecs = ['8', '9', '0']
    
    # Build SDP using caller's codecs
    pbx_sdp = SDPBuilder.build_audio_sdp(
        local_ip='192.168.1.14',
        local_port=10000,
        session_id='test-session',
        codecs=caller_codecs
    )
    
    print("  Generated SDP:")
    for line in pbx_sdp.split('\r\n'):
        if line:
            print(f"    {line}")
    
    # Verify the SDP contains caller's codecs in correct order
    assert 'm=audio 10000 RTP/AVP 8 9 0' in pbx_sdp, "SDP should contain caller's codec order"
    assert 'rtpmap:8 PCMA/8000' in pbx_sdp, "SDP should contain PCMA codec"
    assert 'rtpmap:9 G722/8000' in pbx_sdp, "SDP should contain G722 codec"
    assert 'rtpmap:0 PCMU/8000' in pbx_sdp, "SDP should contain PCMU codec"
    
    print("  ✓ SDP built with caller's codecs")
    print("  ✓ Codec order maintained")


def test_default_codecs_when_none_provided():
    """Test that default codecs are used when caller codecs are None"""
    print("Testing default codec behavior...")
    
    # Build SDP without specifying codecs (should use defaults)
    pbx_sdp = SDPBuilder.build_audio_sdp(
        local_ip='192.168.1.14',
        local_port=10000,
        session_id='test-session'
    )
    
    # Should contain default codecs
    assert 'm=audio 10000 RTP/AVP 0 8 9 101' in pbx_sdp, "SDP should contain default codec order"
    
    print("  ✓ Default codecs used when none provided")


def test_codec_negotiation_scenario():
    """Test full codec negotiation scenario"""
    print("Testing full codec negotiation scenario...")
    
    # Step 1: Phone sends INVITE with SDP offering codecs 8, 9, 0
    phone_sdp_text = """v=0
o=phone 789012 345678 IN IP4 192.168.10.133
s=Call
c=IN IP4 192.168.10.133
t=0 0
m=audio 20000 RTP/AVP 8 9 0
a=rtpmap:8 PCMA/8000
a=rtpmap:9 G722/8000
a=rtpmap:0 PCMU/8000
a=sendrecv
"""
    
    # Step 2: PBX parses phone's SDP
    phone_sdp = SDPSession()
    phone_sdp.parse(phone_sdp_text)
    phone_audio = phone_sdp.get_audio_info()
    phone_codecs = phone_audio['formats']
    
    print(f"  Phone offered codecs: {phone_codecs}")
    
    # Step 3: PBX builds response SDP using phone's codecs
    pbx_sdp = SDPBuilder.build_audio_sdp(
        local_ip='192.168.1.14',
        local_port=10000,
        session_id='call-123',
        codecs=phone_codecs  # Use phone's codecs
    )
    
    # Step 4: Verify PBX's SDP matches phone's codec preferences
    pbx_sdp_parsed = SDPSession()
    pbx_sdp_parsed.parse(pbx_sdp)
    pbx_audio = pbx_sdp_parsed.get_audio_info()
    pbx_codecs = pbx_audio['formats']
    
    print(f"  PBX responded with: {pbx_codecs}")
    
    assert pbx_codecs == phone_codecs, f"PBX codecs {pbx_codecs} should match phone codecs {phone_codecs}"
    
    print("  ✓ Codec negotiation successful")
    print("  ✓ Phone and PBX codec lists match")


def test_partial_codec_support():
    """Test when phone offers codecs we support"""
    print("Testing partial codec support...")
    
    # Phone offers only PCMA and G722 (no PCMU)
    phone_codecs = ['8', '9']
    
    # PBX should accept and use these codecs
    pbx_sdp = SDPBuilder.build_audio_sdp(
        local_ip='192.168.1.14',
        local_port=10000,
        session_id='test-session',
        codecs=phone_codecs
    )
    
    assert 'm=audio 10000 RTP/AVP 8 9' in pbx_sdp, "SDP should contain only offered codecs"
    assert 'rtpmap:8 PCMA/8000' in pbx_sdp, "SDP should contain PCMA"
    assert 'rtpmap:9 G722/8000' in pbx_sdp, "SDP should contain G722"
    # Should not contain PCMU since it wasn't offered
    assert 'rtpmap:0 PCMU/8000' not in pbx_sdp, "SDP should not contain PCMU"
    
    print("  ✓ Partial codec support works correctly")


def run_all_tests():
    """Run all codec negotiation tests"""
    print("=" * 70)
    print("Running Codec Negotiation Tests")
    print("=" * 70)
    print()
    
    tests = [
        test_codec_extraction_from_sdp,
        test_sdp_building_with_caller_codecs,
        test_default_codecs_when_none_provided,
        test_codec_negotiation_scenario,
        test_partial_codec_support
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        print()
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ All codec negotiation tests passed!")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
