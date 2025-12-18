# WebRTC Admin Phone - Zultys ZIP33G Alignment

> **⚠️ DEPRECATED**: This guide has been consolidated into [WEBRTC_GUIDE.md](WEBRTC_GUIDE.md#zultys-phone-alignment). Please refer to the "Zultys Phone Alignment" section in that guide for the most up-to-date information.

## Overview
This document describes the changes made to align the WebRTC browser phone (admin phone) with the Zultys ZIP33G phone configuration to ensure consistent behavior and settings across both phone types.

## Changes Made

### 1. Configuration File Updates (`config.yml`)

Added comprehensive ZIP33G-compatible settings to the `features.webrtc` section:

#### Session Timeout
- **Changed from:** 300 seconds (5 minutes)
- **Changed to:** 3600 seconds (1 hour)
- **Reason:** Matches ZIP33G registration period of 3600s

#### Codec Configuration
Added explicit codec priority matching ZIP33G:
```yaml
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
```

#### DTMF Configuration
Added ZIP33G DTMF settings:
```yaml
dtmf:
  mode: RFC2833              # Primary DTMF method
  payload_type: 101          # RFC2833 payload type
  duration: 160              # DTMF duration in milliseconds
  sip_info_fallback: true    # Enable SIP INFO as fallback
```

#### RTP Settings
```yaml
rtp:
  port_min: 10000            # Minimum RTP port
  port_max: 20000            # Maximum RTP port
  packet_time: 20            # RTP packet time in milliseconds
```

#### NAT Settings
```yaml
nat:
  udp_update_time: 30        # Keep-alive interval in seconds
  rport: true                # Enable rport for NAT traversal
```

#### Audio Settings
```yaml
audio:
  echo_cancellation: true    # Enable echo cancellation
  noise_reduction: true      # Enable noise reduction
  auto_gain_control: true    # Enable automatic gain control
  voice_activity_detection: true  # Enable VAD
  comfort_noise: true        # Enable comfort noise generation
```

### 2. Backend Updates (`pbx/features/webrtc.py`)

#### WebRTCSignalingServer Class
Updated initialization to read all new ZIP33G-compatible settings:
- Session timeout (3600s)
- Codec configuration
- DTMF settings
- RTP port range
- NAT keepalive settings
- Audio processing settings

#### ICE Servers Configuration
Enhanced `get_ice_servers_config()` method to include:
- Codec preferences
- Audio settings for browser
- DTMF configuration

This ensures the browser receives all necessary configuration when creating a WebRTC session.

### 3. Frontend Updates (`admin/js/webrtc_phone.js`)

#### Automatic Microphone Permission Prompt
Added `requestMicrophoneAccess()` method that:
- Automatically requests microphone access when the admin panel loads
- Uses ZIP33G-compatible audio constraints:
  - `echoCancellation: true`
  - `noiseSuppression: true`
  - `autoGainControl: true`
- Provides immediate feedback to users about microphone status
- Releases the stream after permission is granted (actual stream created on call)

#### Initialization Changes
- Modified `initWebRTCPhone()` to be async
- Calls `requestMicrophoneAccess()` automatically on page load
- Provides better user experience by handling permissions upfront

## Settings Alignment Table

| Setting | Zultys ZIP33G | WebRTC Admin Phone (After) | Matched? |
|---------|---------------|---------------------------|----------|
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

## Testing

All changes have been tested and verified:

1. **Unit Tests**: All 11 WebRTC unit tests pass
2. **Configuration Loading**: Settings load correctly from `config.yml`
3. **Settings Verification**: All ZIP33G settings are properly read and applied
4. **Python Syntax**: No syntax errors in Python code
5. **JavaScript Syntax**: No syntax errors in JavaScript code
6. **YAML Syntax**: Configuration file is valid YAML

## Benefits

1. **Consistency**: WebRTC phone now behaves consistently with hardware phones
2. **Better Audio Quality**: Proper codec prioritization (PCMU first)
3. **Reliable DTMF**: RFC2833 ensures DTMF works correctly with voicemail and IVR
4. **NAT Traversal**: Proper NAT keepalive settings prevent connection issues
5. **Audio Processing**: Echo cancellation and noise reduction improve call quality
6. **User Experience**: Automatic microphone permission prompt provides immediate feedback

## Backward Compatibility

All changes are backward compatible:
- Default values are provided for all new settings
- Existing configurations will use sensible defaults
- No breaking changes to APIs or interfaces

## Future Enhancements

Possible future improvements:
1. Allow per-user codec preferences
2. Add UI controls for audio settings
3. Support additional codecs (G.729, Opus)
4. Add QoS marking for WebRTC traffic
