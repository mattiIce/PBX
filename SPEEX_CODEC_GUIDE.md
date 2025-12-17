# Speex Codec Support - Implementation Guide

**Date**: December 17, 2024  
**Status**: ✅ Framework Ready  
**Version**: 1.0

## Overview

Speex is a free, open-source speech codec developed by Xiph.Org Foundation. It's optimized for voice transmission and supports multiple bandwidth modes, variable bitrate, and advanced features like voice activity detection.

## Features

### Codec Capabilities
- **Free and Open Source**: BSD License (royalty-free)
- **Multiple Bandwidths**: Narrowband (8kHz), Wideband (16kHz), Ultra-wideband (32kHz)
- **Variable Bitrate (VBR)**: Adapts to speech complexity
- **Voice Activity Detection (VAD)**: Detects silence periods
- **Discontinuous Transmission (DTX)**: Saves bandwidth during silence
- **Noise Suppression**: Built-in noise reduction
- **Acoustic Echo Cancellation**: Echo cancellation support
- **Quality Levels**: 0-10 configurable quality

### Standards Compliance
- **RFC 5574**: RTP payload format for Speex
- **Xiph.Org Standard**: Open specification
- **IETF Codec**: Widely supported

## Bandwidth Modes

### Narrowband (NB) - 8 kHz
- **Sample Rate**: 8,000 Hz (telephone quality)
- **Bitrate Range**: 2.15 - 24.6 kbps
- **Typical Bitrate**: 8 kbps (quality 8)
- **Frame Size**: 160 samples (20ms)
- **Use Case**: Standard VoIP calls, maximum compatibility

### Wideband (WB) - 16 kHz
- **Sample Rate**: 16,000 Hz (better than telephone)
- **Bitrate Range**: 3.95 - 42.2 kbps
- **Typical Bitrate**: 16 kbps (quality 8)
- **Frame Size**: 320 samples (20ms)
- **Use Case**: HD voice calls, conferencing

### Ultra-wideband (UWB) - 32 kHz
- **Sample Rate**: 32,000 Hz (near CD quality)
- **Bitrate Range**: 4.15 - 44 kbps
- **Typical Bitrate**: 28 kbps (quality 8)
- **Frame Size**: 640 samples (20ms)
- **Use Case**: High-quality voice, music

## Comparison with Other Codecs

| Feature | Speex NB | Speex WB | Opus | G.711 | iLBC |
|---------|----------|----------|------|-------|------|
| **Sample Rate** | 8 kHz | 16 kHz | 8-48 kHz | 8 kHz | 8 kHz |
| **Bitrate (typical)** | 8 kbps | 16 kbps | 32 kbps | 64 kbps | 13.33 kbps |
| **Quality (MOS)** | 3.6-4.1 | 4.0-4.3 | 4.2-4.5 | 4.1 | 3.8-4.0 |
| **VBR Support** | Yes | Yes | Yes | No | No |
| **Complexity** | Low-Medium | Medium | Low-High | Very Low | Low |
| **License** | BSD (Free) | BSD (Free) | BSD (Free) | Free | Free |
| **Status** | Mature | Mature | Modern | Legacy | Niche |

## Installation

### Prerequisites

```bash
# Install Python Speex library
pip install speex

# On some systems, you may need to install system libraries first
# Ubuntu/Debian:
sudo apt-get install libspeex-dev libspeexdsp-dev build-essential python3-dev

# macOS:
brew install speex

# Note: Some Python Speex implementations may require additional setup
```

### Enable in PBX

Add to `config.yml`:

```yaml
codecs:
  speex:
    enabled: true
    mode: nb  # Bandwidth mode: 'nb' (8kHz), 'wb' (16kHz), 'uwb' (32kHz)
    quality: 8  # Quality level 0-10 (8 recommended)
    vbr: true  # Enable Variable Bitrate
    vad: true  # Enable Voice Activity Detection
    dtx: false  # Discontinuous Transmission (optional)
    complexity: 3  # Complexity level 1-10
    payload_type: 97  # Dynamic RTP payload type (97 for nb, 98 for wb, 99 for uwb)
```

## Configuration

### Basic Configuration (Narrowband - Recommended)

```yaml
codecs:
  speex:
    enabled: true
    mode: nb  # 8 kHz narrowband
    quality: 8  # Good quality
    vbr: true  # Variable bitrate
    payload_type: 97
```

### Wideband Configuration (HD Voice)

```yaml
codecs:
  speex:
    enabled: true
    mode: wb  # 16 kHz wideband
    quality: 8
    vbr: true
    payload_type: 98
```

### Low-Bandwidth Configuration

```yaml
codecs:
  speex:
    enabled: true
    mode: nb
    quality: 4  # Lower quality, less bandwidth
    vbr: true
    complexity: 2  # Lower complexity
    payload_type: 97
```

### High-Quality Configuration

```yaml
codecs:
  speex:
    enabled: true
    mode: uwb  # 32 kHz ultra-wideband
    quality: 10  # Highest quality
    vbr: true
    complexity: 8  # Higher complexity for better quality
    payload_type: 99
```

## Usage

### SDP Negotiation

When Speex is enabled, it will be advertised in SDP offers:

**Narrowband (8 kHz)**:
```
m=audio 10000 RTP/AVP 0 8 97 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:97 SPEEX/8000
a=fmtp:97 vbr=on
a=rtpmap:101 telephone-event/8000
```

**Wideband (16 kHz)**:
```
m=audio 10000 RTP/AVP 0 8 98 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:98 SPEEX/16000
a=fmtp:98 vbr=on;mode="1,any"
a=rtpmap:101 telephone-event/8000
```

### Programmatic Usage

```python
from pbx.features.speex_codec import SpeexCodec, SpeexCodecManager

# Initialize codec with narrowband mode
codec = SpeexCodec({
    'mode': 'nb',
    'quality': 8,
    'vbr': True
})

# Check if Speex is available
if codec.is_available():
    # Create encoder and decoder
    codec.create_encoder()
    codec.create_decoder()
    
    # Encode PCM to Speex
    pcm_audio = read_pcm_data()  # 160 samples, 320 bytes for nb mode
    speex_data = codec.encode(pcm_audio)
    
    # Decode Speex to PCM
    decoded_pcm = codec.decode(speex_data)
else:
    print("Speex not available - install speex library")
```

### Using with Call Manager

```python
from pbx.features.speex_codec import SpeexCodecManager

# Initialize manager
manager = SpeexCodecManager(pbx)

# Create codec for new call
codec = manager.create_codec('call-12345', {'mode': 'wb'})
codec.create_encoder()
codec.create_decoder()

# Use during call...

# Clean up when call ends
manager.remove_codec('call-12345')
```

## Performance Characteristics

### Computational Complexity

| Complexity Level | CPU Usage | Quality | Use Case |
|-----------------|-----------|---------|----------|
| 1-2 | Very Low | Fair | Low-power devices |
| 3-5 | Low | Good | Standard VoIP (recommended) |
| 6-8 | Medium | Very Good | High-quality calls |
| 9-10 | High | Excellent | Studio quality |

### Network Requirements

**Narrowband (8 kHz)**:
- **Bandwidth**: 2.15-24.6 kbps (typically 8 kbps)
- **Packet Size**: Variable (VBR)
- **Packet Rate**: 50 packets/second (20ms frames)
- **Total with overhead**: ~20-30 kbps

**Wideband (16 kHz)**:
- **Bandwidth**: 3.95-42.2 kbps (typically 16 kbps)
- **Packet Size**: Variable (VBR)
- **Packet Rate**: 50 packets/second (20ms frames)
- **Total with overhead**: ~25-50 kbps

## When to Use Speex

### ✅ Use Speex When:
- Need open-source codec with BSD license
- Opus is not available or not supported by endpoints
- Want fine-grained quality control (0-10 levels)
- Need variable bitrate for efficiency
- Working with legacy systems that support Speex
- Want voice activity detection built-in
- Bandwidth is moderate to limited

### ❌ Don't Use Speex When:
- Opus is available (Opus is the modern successor)
- Need maximum compatibility (use G.711)
- Network is very reliable (G.711 offers better quality)
- Need lowest possible latency (use G.711)
- Severely bandwidth constrained (use G.729 or Opus at low bitrate)

### Note on Opus vs Speex
Opus is the modern successor to Speex and offers:
- Better quality at all bitrates
- Lower latency
- More flexibility (6-510 kbps range)
- Better packet loss concealment
- Active development and support

**Use Speex when Opus isn't available. For new deployments, prefer Opus.**

## Phone Provisioning

### Supported Phones

Many IP phones support Speex:
- **Grandstream**: GXP series, GRP series (check firmware)
- **Yealink**: T4 series, T5 series (check firmware)
- **Cisco**: SPA series (some models)
- **Polycom**: VVX series (some firmware versions)
- **Softphones**: Wide support (Linphone, Jitsi, Zoiper, etc.)

**Note**: Speex support varies by phone model and firmware. Check your phone's specifications.

### Template Configuration Example

**Yealink Phones**:
```conf
# Speex Codec Configuration
account.1.codec.5.enable = 1
account.1.codec.5.payload_type = SPEEX
account.1.codec.5.priority = 5
```

**Zultys Phones**:
```conf
# Speex Codec (narrowband)
account.1.codec.7.enable = 1
account.1.codec.7.payload_type = 98
account.1.codec.7.priority = 7
account.1.codec.7.name = SPEEX
```

## Troubleshooting

### Problem: Speex not negotiated

**Symptom**: Calls fall back to G.711

**Causes**:
1. Remote endpoint doesn't support Speex
2. Speex disabled in config
3. Phone doesn't have Speex codec
4. Firmware doesn't support Speex

**Solution**:
```bash
# Check config
grep -A 5 "speex:" config.yml

# Verify in SDP offer
# Should see: a=rtpmap:97 SPEEX/8000 (or 16000 for wb)

# Check phone capabilities and firmware version
```

### Problem: "speex library not available" warning

**Symptom**: Warning message on startup

**Solution**:
```bash
# Install speex library
pip install speex

# If that doesn't work, try installing system libraries:
sudo apt-get install libspeex-dev libspeexdsp-dev
pip install speex

# Verify installation
python -c "import speex; print('Speex available')"
```

### Problem: Poor audio quality

**Symptoms**: Robotic or distorted audio

**Causes & Solutions**:

1. **Quality Too Low**
   ```yaml
   speex:
     quality: 8  # Increase from lower value
   ```

2. **Complexity Too Low**
   ```yaml
   speex:
     complexity: 5  # Increase for better quality
   ```

3. **Wrong Bandwidth Mode**
   ```yaml
   speex:
     mode: wb  # Use wideband for better quality
   ```

4. **VBR Issues in Poor Network**
   ```yaml
   speex:
     vbr: false  # Disable VBR for more predictable bitrate
   ```

## API Reference

### SpeexCodec Class

```python
class SpeexCodec:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    def is_available(self) -> bool
    def get_info(self) -> Dict[str, Any]
    def get_sdp_description(self) -> str
    def get_fmtp(self) -> Optional[str]
    def get_sdp_parameters(self) -> Dict[str, Any]
    def create_encoder(self)
    def create_decoder(self)
    def encode(self, pcm_data: bytes) -> Optional[bytes]
    def decode(self, speex_data: bytes) -> Optional[bytes]
    def reset_encoder(self)
    def reset_decoder(self)
```

### SpeexCodecManager Class

```python
class SpeexCodecManager:
    def __init__(self, pbx)
    def create_codec(self, call_id: str, config: Optional[Dict] = None) -> SpeexCodec
    def get_codec(self, call_id: str) -> Optional[SpeexCodec]
    def remove_codec(self, call_id: str)
    def get_all_codecs(self) -> Dict[str, SpeexCodec]
    def is_speex_available(self) -> bool
```

## Best Practices

### Deployment

1. **Use Narrowband for VoIP**: Standard 8kHz is sufficient for most calls
2. **Enable VBR**: Better quality and bandwidth efficiency
3. **Quality Level 8**: Good balance of quality and CPU
4. **Enable VAD**: Reduces bandwidth during silence
5. **Monitor Compatibility**: Not all phones support Speex

### Integration

1. **Codec Priority**: Place Speex after G.711 and iLBC but before G.729
   ```yaml
   # SDP offer: PCMU, PCMA, G722, iLBC, Speex, G729
   codecs: [0, 8, 9, 97, 98, 18]
   ```

2. **Fallback Strategy**: Always have G.711 as backup
3. **Test Before Deployment**: Verify phone firmware supports Speex

## Bandwidth Savings

| Codec | Bitrate | Bandwidth Savings vs G.711 |
|-------|---------|----------------------------|
| G.711 | 64 kbps | Baseline |
| Speex NB (quality 8) | 8 kbps | 87% |
| Speex NB (quality 10) | 24.6 kbps | 62% |
| Speex WB (quality 8) | 16 kbps | 75% |
| Speex UWB (quality 8) | 28 kbps | 56% |

## Resources

### Standards Documents
- [RFC 5574](https://tools.ietf.org/html/rfc5574) - RTP Payload Format for Speex
- [Speex Manual](https://speex.org/docs/manual/speex-manual.pdf) - Official documentation

### External Links
- [Speex Official Website](https://speex.org/) - Xiph.Org Speex project
- [Speex Comparison](https://speex.org/comparison/) - Codec comparisons
- [Xiph.Org Foundation](https://xiph.org/) - Parent organization

### Related PBX Documentation
- [ILBC_CODEC_GUIDE.md](ILBC_CODEC_GUIDE.md) - iLBC codec guide
- [OPUS_CODEC_GUIDE.md](OPUS_CODEC_GUIDE.md) - Opus codec guide (recommended successor)
- [CODEC_COMPARISON_GUIDE.md](CODEC_COMPARISON_GUIDE.md) - Compare all codecs

## Conclusion

Speex is a mature, free, open-source speech codec that offers excellent flexibility and features. While it's being gradually superseded by Opus for new deployments, Speex remains widely deployed and is an excellent choice for systems where Opus isn't available. Its variable bitrate, multiple bandwidth modes, and advanced features like VAD and DTX make it a solid option for VoIP applications.

**Recommendation**: For new deployments, use Opus if available. Use Speex as a fallback option or when working with legacy systems that support Speex but not Opus.

---

**Version**: 1.0  
**Last Updated**: December 17, 2024  
**Status**: ✅ Framework Ready (requires speex library for encoding/decoding)

**Built with ❤️ for flexible VoIP communications**
