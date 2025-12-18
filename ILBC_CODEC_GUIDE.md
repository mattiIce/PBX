# iLBC Codec Support - Implementation Guide

**Date**: December 17, 2024  
**Status**: ✅ Framework Ready  
**Version**: 1.0

## Overview

iLBC (Internet Low Bitrate Codec) is a free, royalty-free speech codec designed specifically for VoIP applications. It excels in environments with packet loss, making it ideal for unreliable network conditions.

## Features

### Codec Capabilities
- **Free and Royalty-Free**: No patent licensing required
- **Two Frame Modes**: 20ms and 30ms frames
- **Low Bitrate**: 13.33-15.2 kbps
- **Built-in PLC**: Packet Loss Concealment is integral to the codec
- **Narrowband**: 8 kHz sampling (telephone quality)
- **Robust**: Designed for packet-switched networks

### Standards Compliance
- **RFC 3951**: iLBC codec definition
- **RFC 3952**: RTP payload format for iLBC
- **IETF Standard**: Widely supported in VoIP systems

## Comparison with Other Codecs

| Feature | iLBC (30ms) | G.729 | Speex NB | G.711 |
|---------|-------------|-------|----------|-------|
| **Bitrate** | 13.33 kbps | 8 kbps | 8-24 kbps | 64 kbps |
| **Sample Rate** | 8 kHz | 8 kHz | 8 kHz | 8 kHz |
| **Packet Loss Resilience** | Excellent | Good | Good | Poor |
| **Computational Cost** | Low | Medium | Low-Medium | Very Low |
| **License** | Free | Licensed | Free | Free |
| **Quality (MOS)** | 3.8-4.0 | 3.9 | 3.6-4.1 | 4.1 |

## Frame Modes

### 20ms Mode
- **Bitrate**: 15.2 kbps
- **Frame Size**: 160 samples (320 bytes PCM)
- **Encoded Size**: 38 bytes
- **Latency**: Lower (20ms frames)
- **Overhead**: Higher (more packets per second)
- **Use Case**: Real-time applications requiring minimal latency

### 30ms Mode (Recommended)
- **Bitrate**: 13.33 kbps
- **Frame Size**: 240 samples (480 bytes PCM)
- **Encoded Size**: 50 bytes
- **Latency**: Moderate (30ms frames)
- **Overhead**: Lower (fewer packets per second)
- **Use Case**: Standard VoIP applications (recommended default)

## Installation

### Prerequisites

**⚠️ IMPORTANT: pyilbc Library Status**

The `pyilbc` package is **not currently available on PyPI**. The iLBC codec framework in this PBX system is fully implemented for SDP negotiation and call setup, but actual audio encoding/decoding requires a compatible library.

**Current Status:**
- ✅ iLBC codec framework is implemented and working
- ✅ SDP negotiation and codec advertising works
- ✅ System gracefully handles missing pyilbc library
- ❌ Audio encoding/decoding requires pyilbc (not available)

**Alternative Options:**

1. **Use Other Codecs**: The PBX supports multiple codecs that are fully functional:
   - Opus (opuslib) - Modern, high-quality codec
   - Speex (speex) - Open source speech codec
   - G.711 (PCMU/PCMA) - Built-in, no library needed
   - G.722 - Wideband codec

2. **Future Installation** (when pyilbc becomes available):
   ```bash
   # This will work when pyilbc is published to PyPI
   pip install pyilbc
   
   # On some systems, you may need to install system libraries first
   # Ubuntu/Debian:
   sudo apt-get install build-essential python3-dev
   
   # macOS:
   brew install python3
   ```

3. **Custom Build**: Advanced users can build iLBC bindings from source if needed

### Enable in PBX

Add to `config.yml`:

```yaml
codecs:
  ilbc:
    enabled: true
    mode: 30  # 20ms or 30ms (30 recommended)
    payload_type: 97  # Dynamic RTP payload type
```

## Configuration

### Basic Configuration (Recommended)

```yaml
codecs:
  ilbc:
    enabled: true
    mode: 30  # 30ms mode for balance of quality and bandwidth
    payload_type: 97
```

### Low-Latency Configuration

```yaml
codecs:
  ilbc:
    enabled: true
    mode: 20  # 20ms mode for lower latency
    payload_type: 97
```

## Usage

### SDP Negotiation

When iLBC is enabled, it will be advertised in SDP offers:

```
m=audio 10000 RTP/AVP 0 8 97 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:97 iLBC/8000
a=fmtp:97 mode=30
a=rtpmap:101 telephone-event/8000
```

### Programmatic Usage

```python
from pbx.features.ilbc_codec import ILBCCodec, ILBCCodecManager

# Initialize codec with 30ms mode
codec = ILBCCodec({'mode': 30})

# Check if iLBC is available
if codec.is_available():
    # Create encoder and decoder
    codec.create_encoder()
    codec.create_decoder()
    
    # Encode PCM to iLBC
    pcm_audio = read_pcm_data()  # 240 samples, 480 bytes for 30ms mode
    ilbc_data = codec.encode(pcm_audio)
    
    # Decode iLBC to PCM
    decoded_pcm = codec.decode(ilbc_data)
    
    # Handle packet loss with PLC
    if packet_lost:
        concealed_audio = codec.handle_packet_loss()
else:
    print("iLBC not available - install pyilbc")
```

### Using with Call Manager

```python
from pbx.features.ilbc_codec import ILBCCodecManager

# Initialize manager
manager = ILBCCodecManager(pbx)

# Create codec for new call
codec = manager.create_codec('call-12345')
codec.create_encoder()
codec.create_decoder()

# Use during call...

# Clean up when call ends
manager.remove_codec('call-12345')
```

## Packet Loss Concealment (PLC)

One of iLBC's key features is built-in packet loss concealment. When a packet is lost:

```python
# Normal packet received
ilbc_packet = receive_rtp_packet()
pcm_audio = codec.decode(ilbc_packet)

# Packet lost!
if packet_lost:
    # Generate concealment audio automatically
    concealed_audio = codec.handle_packet_loss()
    # Play concealed audio instead
    play_audio(concealed_audio)
```

The PLC algorithm:
- Uses past decoded speech to generate plausible audio
- Maintains speech continuity during packet loss
- Works for multiple consecutive lost packets
- Automatically blends back when packets resume

## Performance Characteristics

### Computational Complexity
- **CPU Usage**: ~1.5-2x G.711 (very low)
- **Memory**: Minimal state (<2KB per call)
- **Scalability**: Can handle hundreds of simultaneous calls

### Network Requirements
- **Bandwidth**: 13.33-15.2 kbps + IP/UDP/RTP overhead (~25-30 kbps total)
- **Packet Size**: 38-50 bytes + 40 bytes headers
- **Packet Rate**: 33-50 packets/second
- **Jitter Tolerance**: Excellent (built-in PLC)
- **Packet Loss Tolerance**: Very good (up to 10% loss gracefully handled)

## When to Use iLBC

### ✅ Use iLBC When:
- Network has moderate to high packet loss (>1%)
- Bandwidth is limited but not severely constrained
- Need better quality than G.729 with similar bitrate
- Licensing/patent concerns (iLBC is royalty-free)
- Mobile/wireless scenarios with variable connectivity
- Satellite links with latency and packet loss

### ❌ Don't Use iLBC When:
- Network is very reliable (<0.5% packet loss) - use G.711 or Opus
- Need wideband/HD audio - use G.722 or Opus
- Severely bandwidth constrained - use G.729 (8 kbps)
- Need music quality - use Opus or G.722

## Phone Provisioning

### Supported Phones

Many IP phones support iLBC natively:
- **Grandstream**: GXP series, GRP series
- **Yealink**: T4 series, T5 series
- **Cisco**: SPA series (check firmware)
- **Polycom**: VVX series (check firmware)
- **Softphones**: Most support iLBC (Linphone, Jitsi, etc.)

### Template Configuration Example

```conf
# iLBC Codec Configuration
account.1.codec.4.enable = 1
account.1.codec.4.payload_type = 97
account.1.codec.4.priority = 4
account.1.codec.4.name = iLBC
account.1.codec.4.ptime = 30
```

## Troubleshooting

### Problem: iLBC not negotiated

**Symptom**: Calls fall back to G.711

**Causes**:
1. Remote endpoint doesn't support iLBC
2. iLBC disabled in config
3. Phone doesn't have iLBC codec

**Solution**:
```bash
# Check config
grep -A 3 "ilbc:" config.yml

# Verify in SDP offer
# Should see: a=rtpmap:97 iLBC/8000

# Check phone capabilities
```

### Problem: "pyilbc not available" warning

**Symptom**: Warning message on startup: `"pyilbc library not available - iLBC codec will be negotiated but encoding/decoding will not work"`

**Cause**: The `pyilbc` package is not currently available on PyPI.

**Solution**:

This warning is **expected and normal**. The iLBC codec framework is working correctly for SDP negotiation, but audio encoding/decoding is not available without the pyilbc library.

**Options**:
1. **Ignore the warning**: The system will work fine with other codecs (Opus, Speex, G.711, G.722)
2. **Disable iLBC in config**: If you don't need iLBC codec negotiation, disable it:
   ```yaml
   codecs:
     ilbc:
       enabled: false
   ```
3. **Wait for pyilbc**: When the package becomes available on PyPI, you can install it:
   ```bash
   pip install pyilbc  # Not currently available
   ```

### Problem: Poor audio quality

**Symptoms**: Choppy or distorted audio

**Causes & Solutions**:

1. **High Packet Loss (>10%)**
   - iLBC handles moderate loss well, but >10% degrades quality
   - Check network: `ping -c 100 <remote_ip>`
   - Enable QoS/traffic shaping

2. **Jitter Too High**
   - iLBC tolerates jitter, but extreme values cause issues
   - Increase jitter buffer: 50-100ms recommended

3. **Wrong Frame Size**
   ```python
   # Verify PCM data size
   expected_bytes = 240 * 2  # 30ms mode: 240 samples * 2 bytes
   assert len(pcm_data) == expected_bytes
   ```

## API Reference

### ILBCCodec Class

```python
class ILBCCodec:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    def is_available(self) -> bool
    def get_info(self) -> Dict[str, Any]
    def get_sdp_description(self) -> str
    def get_fmtp(self) -> str
    def get_sdp_parameters(self) -> Dict[str, Any]
    def create_encoder(self)
    def create_decoder(self)
    def encode(self, pcm_data: bytes) -> Optional[bytes]
    def decode(self, ilbc_data: bytes) -> Optional[bytes]
    def handle_packet_loss(self) -> Optional[bytes]
    def reset_encoder(self)
    def reset_decoder(self)
```

### ILBCCodecManager Class

```python
class ILBCCodecManager:
    def __init__(self, pbx)
    def create_codec(self, call_id: str, config: Optional[Dict] = None) -> ILBCCodec
    def get_codec(self, call_id: str) -> Optional[ILBCCodec]
    def remove_codec(self, call_id: str)
    def get_all_codecs(self) -> Dict[str, ILBCCodec]
    def is_ilbc_available(self) -> bool
```

## Best Practices

### Deployment

1. **Use 30ms Mode**: Better bandwidth efficiency, lower overhead
2. **Enable for Mobile Users**: Excellent for wireless/cellular scenarios
3. **Pair with QoS**: Prioritize iLBC traffic for best results
4. **Monitor Packet Loss**: iLBC excels when loss is 1-10%
5. **Fallback Strategy**: Always have G.711 as backup

### Integration

1. **Codec Priority**: Place iLBC after G.711 but before G.729
   ```yaml
   # SDP offer: PCMU, PCMA, iLBC, G.729
   codecs: [0, 8, 97, 18]
   ```

2. **Network Monitoring**: Track packet loss and jitter
3. **Quality Metrics**: Monitor MOS scores for iLBC calls

## Resources

### Standards Documents
- [RFC 3951](https://tools.ietf.org/html/rfc3951) - iLBC Codec Definition
- [RFC 3952](https://tools.ietf.org/html/rfc3952) - RTP Payload Format for iLBC

### External Links
- [RFC 3951](https://tools.ietf.org/html/rfc3951) - iLBC Codec Definition
- [RFC 3952](https://tools.ietf.org/html/rfc3952) - RTP Payload Format for iLBC
- [Global IP Solutions (GIPS)](https://www.gipscorp.com/) - Original iLBC developer
- [WebRTC iLBC](https://webrtc.org/) - iLBC in WebRTC
- **Note**: pyilbc Python bindings are not currently available on PyPI

### Related PBX Documentation
- [CODEC_COMPARISON_GUIDE.md](CODEC_COMPARISON_GUIDE.md) - Compare all codecs
- [SPEEX_CODEC_GUIDE.md](SPEEX_CODEC_GUIDE.md) - Speex codec guide
- [OPUS_CODEC_GUIDE.md](OPUS_CODEC_GUIDE.md) - Opus codec guide

## Conclusion

iLBC is an excellent choice for VoIP deployments where packet loss is a concern. Its royalty-free status, low computational requirements, and built-in packet loss concealment make it ideal for mobile, wireless, and unreliable network scenarios.

**Current Implementation Status:**
- ✅ iLBC codec framework fully implemented
- ✅ SDP negotiation and codec advertising working
- ⚠️ Audio encoding/decoding requires pyilbc library (not available on PyPI)
- ✅ System gracefully handles missing library with appropriate warnings
- 💡 Consider using Opus or Speex codecs as fully-functional alternatives

While the pyilbc library is not currently available, the framework is ready to support it when it becomes available. In the meantime, the PBX system offers excellent alternatives like Opus, Speex, and G.711 that are fully functional.

---

**Version**: 1.1  
**Last Updated**: December 18, 2024  
**Status**: ⚠️ Framework Ready (pyilbc library not available on PyPI)

**Built with ❤️ for robust VoIP communications**
