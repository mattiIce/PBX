# WebRTC Verbose Logging Guide

> **⚠️ DEPRECATED**: This guide has been consolidated into [WEBRTC_GUIDE.md](WEBRTC_GUIDE.md#debugging-and-logging). Please refer to the "Debugging and Logging" section in that guide for the most up-to-date information.

This guide explains how to enable verbose logging for the WebRTC phone feature to debug call failures.

## Overview

Verbose logging provides detailed information about every step of the WebRTC call process, including:
- Session creation
- SDP offer/answer exchange
- ICE candidate gathering
- Connection state changes
- Call initiation
- Error details and stack traces

## Server-Side Logging (Python Backend)

### Enable Verbose Logging

Edit `config.yml` and set `verbose_logging` to `true`:

```yaml
features:
  webrtc:
    enabled: true
    verbose_logging: true  # Enable this for debugging
    session_timeout: 3600
    ...
```

### Restart the Server

After changing the configuration, restart the PBX server:

```bash
# If running directly
python main.py

# If running as a service
sudo systemctl restart pbx
```

### View Logs

Server logs will show `[VERBOSE]` prefixed messages with detailed information:

```bash
# View logs in real-time
tail -f logs/pbx.log

# Or if using console logging
# Logs will appear in terminal output
```

Example verbose log output:
```
2024-12-10 15:30:15 - PBX - INFO - [VERBOSE] WebRTC session creation request:
2024-12-10 15:30:15 - PBX - INFO -   Extension: webrtc-admin
2024-12-10 15:30:15 - PBX - INFO -   Client IP: 192.168.1.100
2024-12-10 15:30:15 - PBX - INFO - [VERBOSE] Session created details:
2024-12-10 15:30:15 - PBX - INFO -   Session ID: 12345678-1234-5678-1234-567812345678
2024-12-10 15:30:15 - PBX - INFO -   Extension: webrtc-admin
2024-12-10 15:30:15 - PBX - INFO -   Total active sessions: 1
```

## Client-Side Logging (Browser Console)

### Enable Browser Verbose Logging

1. Open the admin panel in your browser
2. Open browser console (F12 or right-click → Inspect → Console)
3. Type the following command and press Enter:

```javascript
window.WEBRTC_VERBOSE_LOGGING = true
```

4. Make a call - you'll now see detailed `[VERBOSE]` logs in the console

### View Browser Logs

All verbose logs in the browser console are prefixed with `[VERBOSE]`:

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

## Common Issues and What to Look For

### Issue: Call fails to connect

**Server logs to check:**
- `[VERBOSE] Extension registry check failed` - Target extension doesn't exist
- `[VERBOSE] Session lookup failed` - Session ID mismatch
- `[VERBOSE] Call initiation FAILED` - Check exception details

**Browser logs to check:**
- `Connection state changed: {connectionState: "failed"}` - Network/firewall issue
- `ICE connection FAILED` - STUN/TURN server issues
- `Microphone access error` - Permission denied

### Issue: No audio

**Browser logs to check:**
- `Remote track received` - Check if this appears
- `User media granted` - Verify microphone is working
- Connection states - Verify connection reaches "connected"

### Issue: Call doesn't initiate

**Server logs to check:**
- `[VERBOSE] Creating call through CallManager` - Verify this step
- `[VERBOSE] Call object created` - Check if call object is created
- `[VERBOSE] RTP endpoint info extracted` - Verify media negotiation

**Browser logs to check:**
- `Offer created` - Verify SDP offer is generated
- `Offer response` - Check server accepted the offer
- `Call response data` - Check call initiation succeeded

## Disable Verbose Logging

### Server-Side

Set `verbose_logging: false` in `config.yml` and restart the server.

### Client-Side

In browser console:
```javascript
window.WEBRTC_VERBOSE_LOGGING = false
```

Or simply refresh the page (verbose logging doesn't persist across page reloads).

## Performance Impact

Verbose logging generates significantly more log output and may impact performance slightly:
- **Server**: Minimal impact, suitable for production debugging
- **Browser**: May slow down console rendering with very long calls
- **Recommendation**: Only enable when actively debugging issues

## Additional Tips

1. **Network Tab**: Check browser Network tab (F12) for failed API requests
2. **WebRTC Internals**: Visit `chrome://webrtc-internals` (Chrome) for low-level WebRTC stats
3. **Compare Logs**: Enable both server and client verbose logging simultaneously for complete picture
4. **Log Levels**: Server uses INFO level for verbose logs - ensure logging.level is INFO or DEBUG in config.yml

## Support

If verbose logging reveals an issue you can't resolve:
1. Capture both server and browser logs
2. Note the exact error messages with `[VERBOSE]` prefix
3. Include connection states and timing information
4. Document the steps to reproduce the issue
