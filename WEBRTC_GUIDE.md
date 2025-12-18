# WebRTC Browser Phone Guide

**Last Updated**: December 18, 2024  
**Status**: ✅ Implemented  
**Version**: 2.0

## Overview

The WebRTC Browser Phone feature enables users to make and receive calls directly from their web browser without needing a physical desk phone or software installation. This comprehensive guide covers implementation, configuration, usage, and troubleshooting.

## Table of Contents

1. [User Guide - Making Calls](#user-guide---making-calls)
2. [Configuration](#configuration)
3. [Architecture](#architecture)
4. [API Reference](#api-reference)
5. [Debugging and Logging](#debugging-and-logging)
6. [Zultys Phone Alignment](#zultys-phone-alignment)
7. [Troubleshooting](#troubleshooting)

---

## User Guide - Making Calls

### Accessing the Phone

1. Open the PBX Admin Panel in your web browser: `https://your-pbx-server:8080/admin/`
2. Click on the **"📞 Phone"** tab in the navigation menu
3. The browser phone interface will appear

### Making a Call (Quick Start)

1. The target extension field is pre-filled with **1001** (Operator)
2. Click the **"📞 Call Extension"** button
3. When prompted, **allow microphone access** in your browser
4. Wait for the call to connect
5. Start talking!

### Step-by-Step Guide

#### Step 1: Microphone Permissions

When you click "Call Extension" for the first time, your browser will ask for microphone permissions:

- **Chrome/Edge**: Click "Allow" when prompted
- **Firefox**: Click "Allow" when prompted  
- **Safari**: Click "Allow" when prompted

> **Note**: If you accidentally deny permission, you'll need to manually enable it in your browser settings.

#### Step 2: Calling

1. Enter the extension number you want to call (default: 1001)
2. Click **"📞 Call Extension"**
3. The status will show:
   - "Requesting microphone access..."
   - "Microphone access granted"
   - "Creating WebRTC session..."
   - "Calling extension 1001..."
   - "Call connected" (when the call is answered)

#### Step 3: During the Call

Once connected, you can:

- **Mute/Unmute**: Click the "🔇 Mute" button to mute your microphone
- **Adjust Volume**: Use the volume slider to control speaker volume
- **Hang Up**: Click "📴 Hang Up" to end the call

### Calling Other Extensions

To call a different extension:

1. Clear the extension field
2. Enter the 4-digit extension number (e.g., 1002, 1003)
3. Click **"📞 Call Extension"**

---

## Configuration

### Enable WebRTC in config.yml

```yaml
features:
  webrtc:
    enabled: true
    verbose_logging: false     # Set to true for debugging
    session_timeout: 3600      # Session timeout in seconds (1 hour, matches ZIP33G)
    ice_transport_policy: all  # ICE transport policy: 'all' or 'relay'
    
    # STUN servers for NAT traversal
    stun_servers:
      - stun:stun.l.google.com:19302
      - stun:stun1.l.google.com:19302
    
    # TURN servers for relay (optional)
    turn_servers: []
      # - url: turn:your-turn-server.com:3478
      #   username: your-turn-username
      #   credential: your-turn-password
    
    # Codec Configuration (aligned with ZIP33G)
    codecs:
      - payload_type: 0
        name: PCMU
        priority: 1
        enabled: true
      - payload_type: 8
        name: PCMA
        priority: 2
        enabled: true
      - payload_type: 101
        name: telephone-event
        priority: 3
        enabled: true
    
    # DTMF Configuration
    dtmf:
      mode: RFC2833              # Primary DTMF method
      payload_type: 101          # RFC2833 payload type
      duration: 160              # DTMF duration in milliseconds
      sip_info_fallback: true    # Enable SIP INFO as fallback
    
    # RTP Settings
    rtp:
      port_min: 10000            # Minimum RTP port
      port_max: 20000            # Maximum RTP port
      packet_time: 20            # RTP packet time in milliseconds
    
    # NAT Settings
    nat:
      udp_update_time: 30        # Keep-alive interval in seconds
      rport: true                # Enable rport for NAT traversal
    
    # Audio Settings
    audio:
      echo_cancellation: true    # Enable echo cancellation
      noise_reduction: true      # Enable noise reduction
      auto_gain_control: true    # Enable automatic gain control
      voice_activity_detection: true  # Enable VAD
      comfort_noise: true        # Enable comfort noise generation
```

### Configuration Restart

After changing WebRTC configuration, restart the PBX:

```bash
# If running directly
python main.py

# If running as a service
sudo systemctl restart pbx
```

---

## Architecture

### Components

1. **WebRTCSignalingServer** - Manages WebRTC sessions and handles signaling
2. **WebRTCGateway** - Translates between WebRTC and SIP protocols
3. **REST API Endpoints** - Provides HTTP API for WebRTC operations
4. **WebRTCSession** - Represents an active WebRTC session
5. **Browser Client** (`admin/js/webrtc_phone.js`) - JavaScript WebRTC client

### Flow Diagram

```
Browser Client
    ↓ (HTTP/REST)
WebRTC API Endpoints
    ↓
WebRTCSignalingServer
    ↓ (SDP/ICE)
WebRTCGateway
    ↓ (SIP)
PBX SIP Server
    ↓
Extension/PSTN
```

### Session Lifecycle

1. **Create Session**: Browser requests WebRTC session for extension
2. **Offer/Answer**: SDP offer/answer exchange between browser and PBX
3. **ICE Candidates**: ICE candidates exchanged for NAT traversal
4. **Call Initiation**: Browser requests call to target extension
5. **Media Flow**: RTP media flows between browser and PBX
6. **Teardown**: Call ends, session cleaned up

---

## API Reference

### 1. Create WebRTC Session

Creates a new WebRTC session for an extension.

**Request:**
```bash
POST /api/webrtc/session
Content-Type: application/json

{
  "extension": "1001"
}
```

**Response:**
```json
{
  "success": true,
  "session": {
    "session_id": "abc123-def456",
    "extension": "1001",
    "peer_connection_id": "xyz789",
    "state": "new",
    "created_at": "2025-12-07T12:00:00",
    "last_activity": "2025-12-07T12:00:00"
  },
  "ice_servers": {
    "iceServers": [
      {"urls": "stun:stun.l.google.com:19302"},
      {"urls": "stun:stun1.l.google.com:19302"}
    ],
    "iceTransportPolicy": "all"
  }
}
```

### 2. Send SDP Offer

Send SDP offer from browser to PBX.

**Request:**
```bash
POST /api/webrtc/offer
Content-Type: application/json

{
  "session_id": "abc123-def456",
  "sdp": "v=0\r\no=- ... [full SDP offer]"
}
```

**Response:**
```json
{
  "success": true,
  "sdp": "v=0\r\no=- ... [SDP answer from PBX]"
}
```

### 3. Add ICE Candidate

Add ICE candidate for NAT traversal.

**Request:**
```bash
POST /api/webrtc/candidate
Content-Type: application/json

{
  "session_id": "abc123-def456",
  "candidate": {
    "candidate": "candidate:...",
    "sdpMid": "0",
    "sdpMLineIndex": 0
  }
}
```

**Response:**
```json
{
  "success": true
}
```

### 4. Initiate Call

Start a call to target extension.

**Request:**
```bash
POST /api/webrtc/call
Content-Type: application/json

{
  "session_id": "abc123-def456",
  "target_extension": "1001"
}
```

**Response:**
```json
{
  "success": true,
  "call_id": "call-xyz789"
}
```

### 5. Get Active Sessions

List all active WebRTC sessions.

**Request:**
```bash
GET /api/webrtc/sessions
```

**Response:**
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "abc123-def456",
      "extension": "1001",
      "state": "connected",
      "created_at": "2025-12-07T12:00:00"
    }
  ]
}
```

---

## Debugging and Logging

### Server-Side Verbose Logging

Enable detailed WebRTC logging for debugging call failures.

#### Enable in config.yml

```yaml
features:
  webrtc:
    enabled: true
    verbose_logging: true  # Enable for debugging
```

#### Restart and View Logs

```bash
# Restart PBX
python main.py

# View logs in real-time
tail -f logs/pbx.log | grep VERBOSE

# Or view all logs
tail -f logs/pbx.log
```

#### Example Verbose Output

```
2024-12-10 15:30:15 - PBX - INFO - [VERBOSE] WebRTC session creation request:
2024-12-10 15:30:15 - PBX - INFO -   Extension: webrtc-admin
2024-12-10 15:30:15 - PBX - INFO -   Client IP: 192.168.1.100
2024-12-10 15:30:15 - PBX - INFO - [VERBOSE] Session created details:
2024-12-10 15:30:15 - PBX - INFO -   Session ID: 12345678-1234-5678-1234-567812345678
2024-12-10 15:30:15 - PBX - INFO -   Extension: webrtc-admin
2024-12-10 15:30:15 - PBX - INFO -   Total active sessions: 1
```

### Client-Side Verbose Logging

Enable detailed browser console logging.

#### Enable in Browser Console

1. Open the admin panel
2. Open browser console (F12 or right-click → Inspect → Console)
3. Type and press Enter:

```javascript
window.WEBRTC_VERBOSE_LOGGING = true
```

4. Make a call - you'll see detailed `[VERBOSE]` logs

#### Example Browser Console Output

```
[VERBOSE] WebRTC Phone constructor called: {apiUrl: "http://...", extension: "webrtc-admin"}
[VERBOSE] makeCall() called: {targetExtension: "1001"}
[VERBOSE] Requesting user media...
[VERBOSE] User media granted: {streamId: "...", audioTracks: [...]}
[VERBOSE] Creating WebRTC session: {url: "...", extension: "..."}
[VERBOSE] Session created successfully: {sessionId: "...", iceServers: {...}}
[VERBOSE] RTCPeerConnection created with configuration: {...}
[VERBOSE] ICE candidate event: {candidate: {...}}
```

#### Disable Verbose Logging

Browser:
```javascript
window.WEBRTC_VERBOSE_LOGGING = false
```

Server: Set `verbose_logging: false` in config.yml and restart

### Advanced Debugging Tools

#### Browser WebRTC Internals

Chrome/Edge: Visit `chrome://webrtc-internals`
- View real-time WebRTC statistics
- Monitor ICE candidate pairs
- Check connection states
- Analyze bandwidth usage

#### Network Analysis

In Browser DevTools (F12):
- **Network Tab**: Check for failed API requests
- **Console Tab**: View JavaScript errors and verbose logs
- **Application Tab**: Check for service worker issues (if applicable)

---

## Zultys Phone Alignment

The WebRTC browser phone is configured to match Zultys ZIP33G hardware phone settings for consistency.

### Settings Alignment Table

| Setting | Zultys ZIP33G | WebRTC Browser Phone | Matched? |
|---------|---------------|---------------------|----------|
| Primary Codec | PCMU (0) | PCMU (0) | ✅ |
| Secondary Codec | PCMA (8) | PCMA (8) | ✅ |
| DTMF Method | RFC2833 | RFC2833 | ✅ |
| DTMF Payload | 101 | 101 | ✅ |
| DTMF Duration | 160ms | 160ms | ✅ |
| SIP INFO Fallback | Yes | Yes | ✅ |
| RTP Port Range | 10000-20000 | 10000-20000 | ✅ |
| RTP Packet Time | 20ms | 20ms | ✅ |
| NAT Keepalive | 30s | 30s | ✅ |
| Session Expiry | 3600s | 3600s | ✅ |
| Echo Cancellation | Yes | Yes | ✅ |
| Noise Reduction | Yes | Yes | ✅ |
| Auto Gain Control | Yes | Yes | ✅ |
| VAD | Yes | Yes | ✅ |
| Comfort Noise | Yes | Yes | ✅ |

### Benefits of Alignment

1. **Consistency**: WebRTC phone behaves consistently with hardware phones
2. **Better Audio Quality**: Proper codec prioritization (PCMU first)
3. **Reliable DTMF**: RFC2833 ensures DTMF works correctly with voicemail and IVR
4. **NAT Traversal**: Proper NAT keepalive settings prevent connection issues
5. **Audio Processing**: Echo cancellation and noise reduction improve call quality

---

## Troubleshooting

### No Audio

**Problem**: You can't hear the other person or they can't hear you

**Server Logs to Check** (with verbose logging):
```bash
grep "Remote track" logs/pbx.log
grep "User media granted" logs/pbx.log
grep "connection.*connected" logs/pbx.log
```

**Browser Logs to Check**:
- `Remote track received` - Check if this appears
- `User media granted` - Verify microphone is working
- Connection states - Verify connection reaches "connected"

**Solutions**:
- Check your computer's speaker/headphone volume
- Adjust the volume slider in the phone widget
- Make sure your speakers or headphones are connected properly
- Verify microphone permissions are granted
- Try refreshing the page and calling again
- Check firewall isn't blocking RTP ports (10000-20000)

### Can't Connect

**Problem**: Call won't connect or stays in "Calling..." state

**Server Logs to Check** (with verbose logging):
```bash
grep "Extension registry check" logs/pbx.log
grep "Session lookup" logs/pbx.log
grep "Call initiation" logs/pbx.log
```

**Browser Logs to Check**:
- `Connection state changed: {connectionState: "failed"}` - Network/firewall issue
- `ICE connection FAILED` - STUN/TURN server issues
- `Microphone access error` - Permission denied

**Solutions**:
- Verify the target extension exists and is registered
- Check that WebRTC is enabled in Configuration tab
- Ensure STUN servers are accessible from your network
- Check firewall rules for UDP ports 10000-20000
- Verify NAT/firewall allows WebRTC traffic
- Try from a different network to rule out network issues

### Session Creation Fails

**Problem**: Can't create WebRTC session

**Server Logs to Check**:
```bash
grep "WebRTC session creation" logs/pbx.log
grep "ERROR.*webrtc" logs/pbx.log
```

**Solutions**:
- Verify `webrtc.enabled: true` in config.yml
- Check server logs for specific error messages
- Restart PBX server
- Verify extension exists in configuration

### Session Timeout

**Problem**: Session disconnects after some time

**Configuration**:
The session timeout is set to 3600 seconds (1 hour) by default. To adjust:

```yaml
features:
  webrtc:
    session_timeout: 7200  # 2 hours
```

### Microphone Permission Denied

**Problem**: Browser won't allow microphone access

**Solutions**:
1. **Chrome**: Settings → Privacy and security → Site settings → Microphone → Allow
2. **Firefox**: Settings → Privacy & Security → Permissions → Microphone → Allow
3. **Safari**: Safari → Settings → Websites → Microphone → Allow
4. Try HTTPS instead of HTTP (some browsers require HTTPS for microphone)

### ICE Connection Failed

**Problem**: Connection fails during ICE negotiation

**Server Logs to Check**:
```bash
grep "ICE.*failed" logs/pbx.log
```

**Browser Logs to Check**:
```
ICE connection state: failed
```

**Solutions**:
- Verify STUN servers are reachable
- Add TURN server for symmetric NAT environments
- Check firewall allows UDP traffic
- Ensure router supports WebRTC (some routers block it)

### DTMF Not Working

**Problem**: Can't navigate voicemail or IVR menus

**Configuration Check**:
```yaml
features:
  webrtc:
    dtmf:
      mode: RFC2833              # Should be RFC2833
      payload_type: 101          # Should be 101
      sip_info_fallback: true    # Enable fallback
```

**Solutions**:
- Verify RFC2833 is enabled
- Enable SIP INFO fallback
- Check browser sends DTMF events (console logs)
- See [DTMF_CONFIGURATION_GUIDE.md](DTMF_CONFIGURATION_GUIDE.md) for detailed troubleshooting

---

## Performance Impact

### Verbose Logging

Verbose logging generates significantly more log output:
- **Server**: Minimal impact, suitable for production debugging
- **Browser**: May slow down console rendering with very long calls
- **Recommendation**: Only enable when actively debugging issues

### Resource Usage

- **CPU**: Minimal, WebRTC uses browser's native media engine
- **Bandwidth**: ~64 kbps for PCMU audio codec
- **Memory**: ~10-20 MB per active session

---

## Security Considerations

### HTTPS Requirement

Modern browsers require HTTPS for microphone access. Use:
- Valid SSL certificate (Let's Encrypt recommended)
- Self-signed certificate for testing (users must accept warning)

See [HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md) for SSL configuration.

### STUN/TURN Servers

- **STUN**: Public Google STUN servers are used by default
- **TURN**: Consider running your own TURN server for sensitive deployments
- **Security**: TURN servers should use authentication (username/password)

### Session Management

- Sessions timeout after 1 hour by default
- Inactive sessions are automatically cleaned up
- Session IDs are UUIDs (cryptographically random)

---

## Related Documentation

- **[DTMF_CONFIGURATION_GUIDE.md](DTMF_CONFIGURATION_GUIDE.md)** - DTMF configuration and troubleshooting
- **[CODEC_IMPLEMENTATION_GUIDE.md](CODEC_IMPLEMENTATION_GUIDE.md)** - Audio codec configuration
- **[PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)** - Phone provisioning for hardware phones
- **[HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)** - SSL/TLS configuration
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Full REST API reference
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - General troubleshooting guide

---

**Note**: This consolidated guide replaces the individual WebRTC guides:
- WEBRTC_IMPLEMENTATION_GUIDE.md
- WEBRTC_PHONE_USAGE.md
- WEBRTC_VERBOSE_LOGGING.md
- WEBRTC_ZIP33G_ALIGNMENT.md
