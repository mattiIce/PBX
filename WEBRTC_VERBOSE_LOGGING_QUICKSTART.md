# Quick Start: Enabling WebRTC Verbose Logging

## 1. Enable Server-Side Logging

Edit `config.yml`:
```yaml
features:
  webrtc:
    enabled: true
    verbose_logging: true  # Change this to true
```

Restart PBX server:
```bash
python main.py
```

## 2. Enable Browser-Side Logging

Open browser console (F12) and run:
```javascript
window.WEBRTC_VERBOSE_LOGGING = true
```

## 3. Make a Call and Check Logs

### Server Logs (Terminal):
```
2024-12-10 15:30:15 - PBX - INFO - [VERBOSE] WebRTC session creation request:
2024-12-10 15:30:15 - PBX - INFO -   Extension: webrtc-admin
2024-12-10 15:30:15 - PBX - INFO -   Client IP: 192.168.1.100
...
2024-12-10 15:30:20 - PBX - INFO - [VERBOSE] Call initiation details:
2024-12-10 15:30:20 - PBX - INFO -   Session ID: 12345...
2024-12-10 15:30:20 - PBX - INFO -   Target Extension: 1001
```

### Browser Console:
```
[VERBOSE] makeCall() called: {targetExtension: "1001"}
[VERBOSE] User media granted: {streamId: "...", audioTracks: [...]}
[VERBOSE] Creating WebRTC session: {url: "...", extension: "..."}
[VERBOSE] Session created successfully: {sessionId: "...", iceServers: {...}}
[VERBOSE] ICE candidate event: {candidate: {...}}
...
```

## 4. Common Issues to Look For

- **"Extension registry check failed"** → Target extension doesn't exist
- **"Session lookup failed"** → Session ID mismatch or expired
- **"ICE connection FAILED"** → Network/firewall blocking STUN servers
- **"Microphone access error"** → Browser permissions denied

For full details, see [WEBRTC_VERBOSE_LOGGING.md](WEBRTC_VERBOSE_LOGGING.md)
