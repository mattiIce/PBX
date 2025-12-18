# Audio Codec Implementation Guide

**Last Updated**: December 18, 2024  
**Version**: 2.0

> **Quick Reference**: For a comparison table of all codecs, see [CODEC_COMPARISON_GUIDE.md](CODEC_COMPARISON_GUIDE.md)

## Overview

This comprehensive guide covers the implementation, configuration, and usage of all audio codecs supported by the PBX system. Each codec has different characteristics, making them suitable for different scenarios.

## Table of Contents

1. [G.711 (PCMU/PCMA) - Universal Standard](#g711-pcmupcma---universal-standard)
2. [G.722 - HD Voice Quality](#g722---hd-voice-quality)
3. [Opus - Modern Adaptive Codec](#opus---modern-adaptive-codec)
4. [G.729 - Low Bitrate](#g729---low-bitrate)
5. [G.726 - ADPCM Family](#g726---adpcm-family)
6. [iLBC - Packet Loss Resilience](#ilbc---packet-loss-resilience)
7. [Speex - Open Source Alternative](#speex---open-source-alternative)
8. [Phone-Specific Codec Selection](#phone-specific-codec-selection)
9. [Zultys Phone Codec Configuration](#zultys-phone-codec-configuration)

---

## G.711 (PCMU/PCMA) - Universal Standard

**Status**: ✅ Production Ready  
**License**: Free (Public Domain)

### Overview

G.711 is the universal baseline codec for VoIP. It provides excellent quality with zero compression, making it the most compatible and reliable choice.

### Specifications

- **Bitrate**: 64 kbps
- **Sample Rate**: 8 kHz (narrowband)
- **Compression**: None (PCM)
- **Latency**: <1 ms (algorithmic)
- **MOS**: 4.1 (toll quality)

### Variants

- **PCMU (μ-law)**: Used in North America, Japan (RTP payload type 0)
- **PCMA (A-law)**: Used in Europe, rest of world (RTP payload type 8)

### Configuration

G.711 is enabled by default and requires no special configuration:

```yaml
codecs:
  enabled:
    - PCMU
    - PCMA
```

### When to Use

- ✅ Default choice for LAN deployments
- ✅ Maximum compatibility required
- ✅ Lowest latency needed
- ✅ Ample bandwidth available

### Limitations

- ❌ High bandwidth usage (64 kbps)
- ❌ No packet loss concealment
- ❌ Narrowband only (8 kHz)

---

## G.722 - HD Voice Quality

**Status**: ✅ Production Ready  
**License**: Free  
**Date Implemented**: December 10, 2025

### Overview

G.722 is a wideband audio codec that provides excellent voice quality at 16 kHz sampling rate with minimal latency. It delivers HD audio quality while using the same bandwidth as G.711.

### Specifications

- **Bitrate**: 48, 56, and 64 kbps
- **Sample Rate**: 16 kHz (wideband) - 7 kHz audio bandwidth
- **Compression**: SB-ADPCM (Sub-band Adaptive Differential PCM)
- **Latency**: ~20-40 ms algorithmic delay
- **MOS**: 4.3-4.5 (excellent quality)
- **RTP Payload Type**: 9 (default)
- **SDP Clock Rate**: 8000 (RFC 3551 quirk - actual sampling is 16 kHz)

### Standards Compliance

- **ITU-T G.722**: Wideband audio codec standard
- **RFC 3551**: RTP payload format for G.722
- **SIP/SDP**: Full integration with SIP signaling and SDP negotiation

### Architecture

```
G.722 Codec System
├── G722Codec (pbx/features/g722_codec.py)
│   ├── Encoder (PCM → G.722)
│   ├── Decoder (G.722 → PCM)
│   ├── SDP Parameter Generation
│   └── Configuration Management
└── G722CodecManager
    ├── Per-call codec instances
    ├── Global configuration
    └── Lifecycle management
```

### Configuration

#### Enable in config.yml

Add G.722 to your codec list:

```yaml
# Top-level Codec Configuration
codecs:
  enabled:
    - G722    # HD voice codec (16 kHz)
    - PCMU    # Fallback for compatibility
    - PCMA    # International fallback
  
  # Codec priority (offer in this order during SDP negotiation)
  priority:
    - G722    # Prefer HD quality
    - PCMU
    - PCMA

# WebRTC-specific codec configuration (if using WebRTC phones)
webrtc:
  codecs:
    - G722
    - PCMU
    - PCMA
```

### Phone Provisioning

#### Supported Phones

G.722 is widely supported by modern IP phones:

- ✅ Zultys ZIP 33G/37G/57G
- ✅ Yealink T4x/T5x series
- ✅ Polycom VVX series
- ✅ Cisco 79xx/88xx series
- ✅ Grandstream GXP/GRP series
- ✅ Most WebRTC-compatible browsers

#### Template Configuration

For Zultys phones, G.722 is configured in the provisioning template:

```xml
<!-- ZIP33G/ZIP37G Configuration -->
<Codec_1>G.722</Codec_1>
<Codec_1_BitRate>64000</Codec_1_BitRate>
<Codec_1_PacketSize>20</Codec_1_PacketSize>
```

### When to Use

- ✅ HD voice quality desired
- ✅ Modern IP phones available
- ✅ Same bandwidth as G.711 acceptable
- ✅ Better speech clarity important

### Limitations

- ❌ Higher CPU than G.711
- ❌ Still requires 64 kbps bandwidth
- ❌ Limited to 16 kHz (not full wideband)

---

## Opus - Modern Adaptive Codec

**Status**: ✅ Production Ready  
**License**: BSD (Royalty-free)  
**Date Implemented**: December 8, 2025

### Overview

Opus is a modern, versatile audio codec that provides excellent quality at low bitrates with minimal latency. It's the codec of choice for modern VoIP applications and WebRTC.

### Specifications

- **Bitrate**: 6 kbps to 510 kbps (adaptive)
- **Sample Rates**: 8, 12, 16, 24, 48 kHz (adaptive)
- **Latency**: 5-66.5 ms
- **MOS**: 4.2-4.7 (varies by bitrate)
- **Compression**: Hybrid SILK/CELT
- **RTP Payload Type**: 111 (dynamic, configurable)

### Advanced Features

- **Adaptive Bitrate**: Automatically adjusts to network conditions
- **Packet Loss Concealment**: Advanced error recovery
- **Forward Error Correction (FEC)**: Optional redundancy
- **Variable Bandwidth**: Switches between NB/WB/SWB/FB
- **Low Latency**: Optimized for real-time communication
- **Constant Bitrate (CBR)**: For predictable bandwidth
- **Variable Bitrate (VBR)**: For optimal quality

### Standards Compliance

- **RFC 6716**: Opus Codec Definition
- **RFC 7587**: RTP Payload Format for Opus
- **WebRTC Mandatory**: Required codec for WebRTC

### Application Types

Opus supports three application profiles:

1. **VOIP**: Optimized for speech (recommended for PBX)
   - Lower latency
   - Speech-optimized processing
   - Better for VoIP applications

2. **Audio**: Optimized for music
   - Higher quality
   - Full-band audio
   - Better for music streaming

3. **Restricted Low Delay**: Ultra-low latency
   - Minimal buffering
   - For interactive applications
   - Slightly lower quality

### Installation

#### Prerequisites

Install the Opus codec library and Python bindings:

```bash
# Install opuslib Python library
pip install opuslib

# On Ubuntu/Debian, install Opus libraries
sudo apt-get install libopus0 libopus-dev

# On macOS
brew install opus

# On Windows
# Download pre-built binaries from xiph.org
```

#### Enable in PBX

```yaml
codecs:
  enabled:
    - OPUS
    - G722
    - PCMU
    - PCMA
  
  priority:
    - OPUS    # Prefer modern codec
    - G722    # HD fallback
    - PCMU    # Universal fallback

  # Opus-specific configuration
  opus:
    bitrate: 32000        # 32 kbps (16-64 recommended for voice)
    sample_rate: 48000    # 48 kHz (full-band)
    channels: 1           # Mono for telephony
    application: voip     # voip|audio|restricted_lowdelay
    complexity: 10        # 0-10 (10 = best quality, higher CPU)
    packet_loss: 10       # Expected packet loss % (0-100)
    use_fec: true         # Forward Error Correction
    use_dtx: true         # Discontinuous Transmission (silence detection)
```

### When to Use

- ✅ WebRTC phones or browser-based calling
- ✅ Variable network conditions
- ✅ Modern infrastructure
- ✅ Bandwidth optimization needed
- ✅ Excellent quality at low bitrates desired

### Limitations

- ❌ Requires library installation
- ❌ Higher CPU usage than G.711
- ❌ Not all legacy phones support it

---

## G.729 - Low Bitrate

**Status**: ⚙️ Framework Ready (Codec negotiation supported)  
**License**: Licensed (Patent-encumbered, licenses available)

### Overview

G.729 is a low-bitrate speech codec that provides good quality at only 8 kbps. While the PBX supports G.729 negotiation, actual encoding/decoding requires licensed software or hardware.

### Specifications

- **Bitrate**: 8 kbps
- **Sample Rate**: 8 kHz (narrowband)
- **Compression**: CS-ACELP
- **Latency**: 25-35 ms
- **MOS**: 3.9 (good quality)
- **RTP Payload Type**: 18 (default)

### Configuration

```yaml
codecs:
  enabled:
    - G729
    - PCMU    # Always include fallback
    - PCMA
  
  priority:
    - G729    # Prefer low bandwidth
    - PCMU
```

### Implementation Status

The PBX currently provides:
- ✅ SDP negotiation for G.729
- ✅ Codec selection and priority
- ✅ RTP packet handling structure
- ⚠️ Encoding/decoding requires external library or hardware DSP

### When to Use

- ✅ Severely limited bandwidth (WAN links)
- ✅ License costs acceptable
- ✅ Multiple simultaneous calls over limited connection
- ✅ Hardware acceleration available

### Limitations

- ❌ Patent licensing required
- ❌ Narrowband only (8 kHz)
- ❌ Computational complexity
- ❌ Lower quality than G.711/G.722

---

## G.726 - ADPCM Family

**Status**: ✅ Partial Support  
**License**: Free

### Overview

G.726 is a family of ADPCM codecs offering multiple bitrate options (16/24/32/40 kbps). The PBX system provides negotiation support for all variants.

### Specifications

| Variant | Bitrate | Payload Type | Quality (MOS) |
|---------|---------|--------------|---------------|
| G.726-16 | 16 kbps | 112 (dynamic) | 3.4 |
| G.726-24 | 24 kbps | 113 (dynamic) | 3.6 |
| G.726-32 | 32 kbps | 2 or 114 | 3.8 |
| G.726-40 | 40 kbps | 115 (dynamic) | 3.9 |

- **Sample Rate**: 8 kHz (narrowband)
- **Compression**: ADPCM
- **Latency**: ~1-5 ms
- **Use Case**: Legacy system compatibility

### Configuration

```yaml
codecs:
  enabled:
    - G726-32   # Most common variant
    - PCMU
    - PCMA
  
  priority:
    - G726-32
    - PCMU
```

### SDP Example

```
m=audio 10000 RTP/AVP 114 0 8
a=rtpmap:114 G726-32/8000
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
```

### Implementation Status

- ✅ SDP negotiation for all G.726 variants
- ✅ Codec selection and priority
- ⚠️ Encoding/decoding requires implementation

### When to Use

- ✅ Legacy system compatibility
- ✅ Moderate bandwidth savings needed
- ✅ Better quality than G.729 desired

### Limitations

- ❌ Less efficient than modern codecs
- ❌ Narrowband only (8 kHz)
- ❌ Limited phone support

---

## iLBC - Packet Loss Resilience

**Status**: ✅ Framework Ready  
**License**: Free (Royalty-free)  
**Standard**: RFC 3951

### Overview

iLBC (Internet Low Bitrate Codec) is a free, royalty-free speech codec designed specifically for VoIP applications. It excels in environments with packet loss, making it ideal for unreliable network conditions.

### Specifications

- **Bitrate**: 13.33 kbps (30ms) or 15.2 kbps (20ms)
- **Sample Rate**: 8 kHz (narrowband)
- **Frame Sizes**: 20ms or 30ms
- **Latency**: 20-30 ms
- **MOS**: 3.8-4.0
- **Packet Loss Resilience**: Excellent (up to 5% loss with minimal quality degradation)

### Standards Compliance

- **RFC 3951**: iLBC Codec Specification
- **RFC 3952**: RTP Payload Format
- **IETF Standard**: Fully standardized

### Frame Modes

#### 20ms Mode
- **Bitrate**: 15.2 kbps
- **Frame Size**: 20 ms (38 bytes)
- **Use Case**: Lower latency applications
- **Quality**: Slightly lower

#### 30ms Mode (Recommended)
- **Bitrate**: 13.33 kbps
- **Frame Size**: 30 ms (50 bytes)
- **Use Case**: Better quality, standard VoIP
- **Quality**: Better overall performance

### Installation

#### Prerequisites

```bash
# Install Python iLBC library (if available)
# Note: iLBC support may require compilation from source
# Check availability: pip search ilbc
```

#### Enable in PBX

```yaml
codecs:
  enabled:
    - ILBC
    - PCMU
    - PCMA
  
  priority:
    - ILBC
    - PCMU

  # iLBC-specific configuration
  ilbc:
    mode: 30    # 20 or 30 ms (30 recommended)
```

### When to Use

- ✅ Unreliable network conditions
- ✅ High packet loss expected (>1%)
- ✅ Low bandwidth requirements
- ✅ Free/open source requirement
- ✅ Mobile or wireless networks

### Limitations

- ❌ Narrowband only (8 kHz)
- ❌ Limited phone support
- ❌ Lower quality than G.711/G.722
- ❌ May require library installation

---

## Speex - Open Source Alternative

**Status**: ✅ Framework Ready  
**License**: BSD (Royalty-free)  
**Note**: Largely superseded by Opus

### Overview

Speex is a free, open-source speech codec developed by Xiph.Org Foundation. While it has been largely superseded by Opus, it remains useful for legacy compatibility.

### Specifications

- **Bitrate**: 2.15 to 44 kbps (variable)
- **Sample Rates**: 8, 16, 32 kHz (narrowband, wideband, ultra-wideband)
- **Compression**: CELP-based
- **Latency**: 30-34 ms
- **MOS**: 3.6-4.3 (varies by mode and bitrate)

### Standards Compliance

- **RFC 5574**: RTP Payload Format for Speex
- **Xiph.Org**: Open source, BSD license

### Bandwidth Modes

#### Narrowband (NB) - 8 kHz
- **Sample Rate**: 8 kHz
- **Bitrate**: 2.15-24.6 kbps
- **Use Case**: Standard telephony
- **Quality**: 3.6-3.9 MOS

#### Wideband (WB) - 16 kHz
- **Sample Rate**: 16 kHz
- **Bitrate**: 4-44 kbps
- **Use Case**: HD voice
- **Quality**: 4.0-4.3 MOS

#### Ultra-wideband (UWB) - 32 kHz
- **Sample Rate**: 32 kHz
- **Bitrate**: Higher bitrates
- **Use Case**: High-quality audio
- **Quality**: Professional quality

### Installation

#### Prerequisites

```bash
# Install Python Speex library (if available)
# On some systems, you may need to install system libraries first

# Ubuntu/Debian:
sudo apt-get install libspeex1 libspeex-dev

# macOS:
brew install speex

# Note: Some Python Speex implementations may require additional setup
```

#### Enable in PBX

```yaml
codecs:
  enabled:
    - SPEEX
    - PCMU
    - PCMA
  
  priority:
    - SPEEX
    - PCMU

  # Speex-specific configuration
  speex:
    mode: wideband    # narrowband|wideband|ultra-wideband
    quality: 8        # 0-10 (higher = better quality, more CPU)
    complexity: 3     # 1-10 (computational complexity)
    vbr: true        # Variable bitrate
    vad: true        # Voice Activity Detection
```

### When to Use

- ✅ Legacy Speex infrastructure
- ✅ Open source requirement
- ✅ Variable bitrate needed
- ⚠️ Consider Opus instead for new deployments

### Limitations

- ❌ Superseded by Opus (better quality/efficiency)
- ❌ Limited modern phone support
- ❌ May require library installation

### Migration Note

**Recommendation**: For new deployments, use **Opus** instead of Speex. Opus provides better quality, lower latency, and wider industry support while maintaining the same open-source benefits.

---

## Phone-Specific Codec Selection

**Date Implemented**: December 12, 2025

### Overview

The PBX server automatically selects appropriate codecs based on the detected phone model when establishing calls. This ensures optimal compatibility and audio quality for different phone models.

### Supported Phone Models

#### Zultys ZIP37G
- **Server-side codec offering**: PCMU/PCMA only
- **Payload types**: 0 (PCMU), 8 (PCMA), 101 (RFC2833 DTMF)
- **Reason**: ZIP37G phones natively support PCMU/PCMA with built-in codec defaults
- **Audio Quality**: Excellent with PCMU/PCMA

#### Zultys ZIP33G
- **Server-side codec offering**: Full codec suite with explicit parameters
- **Codecs**: G.722, PCMU, PCMA with detailed SDP parameters
- **Payload types**: 9 (G.722), 0 (PCMU), 8 (PCMA), 101 (RFC2833 DTMF)
- **Reason**: ZIP33G requires explicit codec configuration for proper operation
- **Audio Quality**: HD voice with G.722 support

### Implementation

The PBX automatically detects the phone model from the SIP User-Agent header and adjusts codec offerings accordingly:

```python
def get_codecs_for_phone_model(user_agent):
    """Select codecs based on phone model"""
    if "ZIP37G" in user_agent:
        # ZIP37G: Simple PCMU/PCMA only
        return ["PCMU", "PCMA"]
    elif "ZIP33G" in user_agent:
        # ZIP33G: Full codec suite
        return ["G722", "PCMU", "PCMA"]
    else:
        # Default: Offer all enabled codecs
        return config.get('codecs', {}).get('enabled', [])
```

### Benefits

- ✅ Automatic optimization per phone model
- ✅ Eliminates codec negotiation issues
- ✅ Ensures maximum audio quality
- ✅ Reduces configuration complexity
- ✅ Prevents compatibility problems

---

## Zultys Phone Codec Configuration

### ZIP33G vs ZIP37G Differences

**Date**: December 11, 2025

The Zultys ZIP33G and ZIP37G IP phones have different codec configuration requirements:

#### ZIP37G Configuration
- **Native Support**: PCMU/PCMA codecs work with minimal configuration
- **No Explicit Params Needed**: Built-in defaults handle codec negotiation
- **SDP Simplicity**: Basic SDP attributes sufficient

#### ZIP33G Configuration
- **Explicit Parameters Required**: Needs detailed codec configuration
- **SDP Requirements**: Must specify sample rates, packet sizes, bitrates
- **Configuration Complexity**: Requires provisioning template customization

### ZIP33G Codec Configuration Template

For optimal ZIP33G performance, use the following provisioning template parameters:

```xml
<!-- PCMU Configuration -->
<Codec_2>PCMU</Codec_2>
<Codec_2_BitRate>64000</Codec_2_BitRate>
<Codec_2_PacketSize>20</Codec_2_PacketSize>
<Codec_2_SampleRate>8000</Codec_2_SampleRate>

<!-- PCMA Configuration -->
<Codec_3>PCMA</Codec_3>
<Codec_3_BitRate>64000</Codec_3_BitRate>
<Codec_3_PacketSize>20</Codec_3_PacketSize>
<Codec_3_SampleRate>8000</Codec_3_SampleRate>

<!-- G.722 Configuration (if supported) -->
<Codec_1>G.722</Codec_1>
<Codec_1_BitRate>64000</Codec_1_BitRate>
<Codec_1_PacketSize>20</Codec_1_PacketSize>
```

### SDP Generation

The PBX generates appropriate SDP offers based on phone model:

**For ZIP37G** (simple):
```
m=audio 10000 RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
```

**For ZIP33G** (detailed):
```
m=audio 10000 RTP/AVP 9 0 8 101
a=rtpmap:9 G722/8000
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=ptime:20
a=fmtp:9 bitrate=64000
```

### Troubleshooting

If ZIP33G phones have audio issues:

1. **Verify Provisioning**: Ensure codec parameters are in provisioning template
2. **Check SDP**: Verify server sends detailed codec parameters
3. **Test with PCMU Only**: Simplify to PCMU-only to isolate issues
4. **Update Firmware**: Ensure phone firmware is current
5. **Review Logs**: Check for codec negotiation failures

See [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md) for detailed provisioning configuration.

---

## General Codec Configuration Best Practices

### Codec Priority Order

Always include fallback codecs for maximum compatibility:

```yaml
codecs:
  priority:
    - OPUS     # Modern, high quality (if available)
    - G722     # HD voice fallback
    - PCMU     # Universal fallback
    - PCMA     # International fallback
```

### RTP Payload Types

Standard payload types:
- **0**: PCMU
- **8**: PCMA
- **9**: G.722
- **18**: G.729
- **101**: telephone-event (DTMF - RFC2833)
- **111+**: Dynamic (Opus, iLBC, Speex, etc.)

### Testing Codecs

To test codec negotiation:

1. **Check Phone Capabilities**: Review phone's supported codecs
2. **Monitor SDP**: Use SIP traces to verify codec offers
3. **Test Audio Quality**: Make test calls with each codec
4. **Measure Bandwidth**: Monitor RTP stream bitrates
5. **Test Packet Loss**: Verify behavior under degraded conditions

---

## Additional Resources

### Related Documentation

- **[CODEC_COMPARISON_GUIDE.md](CODEC_COMPARISON_GUIDE.md)** - Codec comparison matrix and decision guide
- **[PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)** - Phone provisioning and codec configuration
- **[DTMF_CONFIGURATION_GUIDE.md](DTMF_CONFIGURATION_GUIDE.md)** - DTMF payload type configuration
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Audio troubleshooting

### External Standards

- ITU-T G.711: https://www.itu.int/rec/T-REC-G.711
- ITU-T G.722: https://www.itu.int/rec/T-REC-G.722
- RFC 6716 (Opus): https://tools.ietf.org/html/rfc6716
- RFC 3951 (iLBC): https://tools.ietf.org/html/rfc3951
- RFC 5574 (Speex): https://tools.ietf.org/html/rfc5574

---

**Note**: This consolidated guide replaces the individual codec guides. For the comparison matrix and decision flowchart, see [CODEC_COMPARISON_GUIDE.md](CODEC_COMPARISON_GUIDE.md).
