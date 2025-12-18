# WebRTC Browser Phone - User Guide

> **⚠️ DEPRECATED**: This guide has been consolidated into [WEBRTC_GUIDE.md](WEBRTC_GUIDE.md). Please refer to the consolidated guide for the most up-to-date information on using the WebRTC browser phone.

## Overview

The WebRTC Browser Phone feature allows you to make and receive phone calls directly from your web browser without needing a physical desk phone. This is perfect for working from home or when you don't have access to your office phone.

## Accessing the Phone

1. Open the PBX Admin Panel in your web browser: `http://your-pbx-server:8080/admin/`
2. Click on the **"📞 Phone"** tab in the navigation menu
3. The browser phone interface will appear

## Making a Call to Extension 1001 (Operator)

### Quick Start

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

## Calling Other Extensions

To call a different extension:

1. Clear the extension field
2. Enter the 4-digit extension number (e.g., 1002, 1003)
3. Click **"📞 Call Extension"**

## Troubleshooting

### No Audio

**Problem**: You can't hear the other person

**Solutions**:
- Check your computer's speaker/headphone volume
- Adjust the volume slider in the phone widget
- Make sure your speakers or headphones are connected properly
- Try refreshing the page and calling again

### Can't Connect

**Problem**: Call won't connect or stays in "Calling..." state

**Solutions**:
- Verify the target extension exists and is registered
- Check that WebRTC is enabled in the Configuration tab
- Ensure your network allows WebRTC/SIP traffic
- Check the browser console for error messages (F12)

### Echo or Feedback

**Problem**: You hear an echo or feedback during the call

**Solutions**:
- **Use headphones** - This is the best solution
- Reduce your speaker volume
- Move your microphone away from your speakers

### Microphone Not Working

**Problem**: The other person can't hear you

**Solutions**:
- Check if you're muted (unmute button should say "🔇 Mute")
- Verify microphone permissions in browser settings:
  - **Chrome**: Settings → Privacy & Security → Site Settings → Microphone
  - **Firefox**: Settings → Privacy & Security → Permissions → Microphone
  - **Safari**: Safari → Preferences → Websites → Microphone
- Try a different browser
- Check your operating system's microphone settings

### Browser Compatibility

The WebRTC phone works best in:
- ✅ **Chrome/Chromium** (Recommended)
- ✅ **Microsoft Edge** (Recommended)
- ✅ **Firefox**
- ⚠️ **Safari** (May have limited support)

> **Note**: Internet Explorer is not supported.

## Security Considerations

### Microphone Access

- The browser phone only accesses your microphone during active calls
- You can revoke microphone permissions at any time in your browser settings
- The PBX system does not record calls through the browser phone unless explicitly configured

### Network Security

- WebRTC connections use STUN/TURN servers for NAT traversal
- Audio is transmitted in real-time over RTP (Real-time Transport Protocol)
- For enhanced security, enable SRTP (Secure RTP) in the PBX configuration

## Advanced Features

### Volume Control

The volume slider controls the volume of the incoming audio (the person you're talking to). Your own microphone volume is controlled by your operating system's settings.

### Mute

When muted:
- Your microphone is disabled
- The other person cannot hear you
- You can still hear them
- The mute button will turn red and pulse

### Call Status

The status indicator shows different colors:
- 🔵 **Blue** (Info): Normal operation status
- 🟢 **Green** (Success): Connected and working
- 🟡 **Yellow** (Warning): Minor issues or disconnected
- 🔴 **Red** (Error): Critical error or failure

## Tips for Best Call Quality

1. **Use a wired network connection** when possible (more stable than WiFi)
2. **Close bandwidth-heavy applications** (streaming video, downloads)
3. **Use headphones** to prevent echo
4. **Choose a quiet environment** for better audio clarity
5. **Use a quality microphone** if possible (USB headset recommended)

## Working from Home

This feature is specifically designed for remote work scenarios:

- ✅ No VPN required (works over internet)
- ✅ No software installation needed
- ✅ Works on any computer with a web browser
- ✅ Just needs microphone access
- ✅ Same call quality as office phone

## Getting Help

If you continue to experience issues:

1. Check the **Troubleshooting** section above
2. Press F12 to open browser developer tools and check for errors
3. Contact your system administrator
4. Include:
   - Browser type and version
   - Error messages from console
   - Steps you took before the issue occurred

## Technical Details

For administrators and technical users:

- **Protocol**: WebRTC (Web Real-Time Communication)
- **Signaling**: REST API over HTTP
- **Media**: RTP/SRTP over UDP
- **NAT Traversal**: STUN/TURN servers
- **Codecs**: G.711, Opus (depends on PBX configuration)
- **Session Timeout**: 5 minutes (configurable)

## Configuration

WebRTC settings can be configured in the PBX's `config.yml`:

```yaml
features:
  webrtc:
    enabled: true
    session_timeout: 300
    ice_transport_policy: all
    stun_servers:
      - stun:stun.l.google.com:19302
```

See `WEBRTC_IMPLEMENTATION_GUIDE.md` for complete configuration details.

---

**Last Updated**: December 2024  
**Feature Status**: ✅ Production Ready
