# WebRTC Audio Troubleshooting Guide

Generated: 2025-12-19T15:37:22.302592


WEBRTC AUDIO TROUBLESHOOTING CHECKLIST

1. Basic Checks:
   □ Is WebRTC enabled in config.yml?
   □ Are STUN servers configured?
   □ Is the browser supported (Chrome/Firefox/Safari/Edge)?
   □ Are microphone permissions granted?

2. Network Checks:
   □ Can the browser reach STUN servers?
   □ Are UDP ports 10000-20000 open?
   □ Is there a NAT/firewall blocking RTP?
   □ Are TURN servers needed for restrictive networks?

3. Codec Checks:
   □ Is Opus codec available?
   □ Does the SDP offer include expected codecs?
   □ Is codec negotiation succeeding?
   □ Are sample rates compatible (48kHz for Opus, 8kHz for G.711)?

4. Audio Quality Checks:
   □ Is echo cancellation enabled?
   □ Is noise suppression enabled?
   □ Is the bitrate appropriate for network conditions?
   □ Are there packet loss issues?

5. Browser Console Checks:
   □ Check for WebRTC errors in console
   □ Check getUserMedia() success
   □ Check ICE candidate gathering
   □ Check RTP statistics (chrome://webrtc-internals)

6. Server-Side Checks:
   □ Check SIP registration status
   □ Check RTP proxy configuration
   □ Check codec transcoding if needed
   □ Check server firewall rules

7. Testing Tools:
   □ Use chrome://webrtc-internals for debugging
   □ Use about:webrtc in Firefox
   □ Test with simple HTML WebRTC page first
   □ Compare with known-working WebRTC service


## Test Results

- Passed: 6
- Failed: 0
- Warnings: 0
