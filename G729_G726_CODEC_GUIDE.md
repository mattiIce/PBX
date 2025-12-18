# G.729 and G.726 Codec Support Guide

> **⚠️ DEPRECATED**: This guide has been consolidated into [CODEC_IMPLEMENTATION_GUIDE.md](CODEC_IMPLEMENTATION_GUIDE.md). Please refer to the consolidated guide for the most up-to-date information on all codecs including G.729 and G.726.

This guide explains the G.729 and G.726 codec support in the PBX system, including configuration, capabilities, and limitations.

## Overview

The PBX system now supports additional codecs beyond the basic G.711 (PCMU/PCMA) and G.722:

- **G.729**: Low-bitrate speech codec (8 kbit/s) - Framework support with codec negotiation
- **G.726**: Variable-rate ADPCM codec with multiple bitrate variants (16/24/32/40 kbit/s)

## Codec Details

### G.729 - Low Bitrate Codec

**Specifications:**
- **Bitrate**: 8 kbit/s
- **Sample Rate**: 8 kHz (narrowband)
- **Frame Size**: 10 ms (80 samples)
- **RTP Payload Type**: 18 (standard static type)
- **Quality**: Good narrowband speech quality
- **Bandwidth**: Very low (excellent for constrained networks)

**Variants:**
- **G.729**: Original version
- **G.729A**: Simplified version with slightly reduced quality (most common)
- **G.729B**: Adds Voice Activity Detection (VAD) and Comfort Noise Generation (CNG)
- **G.729AB**: Combines A and B features (recommended default)

**Use Cases:**
- VoIP over low-bandwidth connections (satellite, slow DSL, cellular)
- High-density call servers (reduced bandwidth per call)
- International calls where bandwidth is expensive
- Mobile/remote office scenarios

**Licensing Note:**
G.729 may require patent licensing depending on your jurisdiction and use case. Always verify licensing requirements for commercial deployment.

### G.726 - ADPCM Codec Family

**Specifications:**
- **Bitrates**: 16, 24, 32, or 40 kbit/s
- **Sample Rate**: 8 kHz (narrowband)
- **Encoding**: Adaptive Differential Pulse Code Modulation (ADPCM)
- **Quality**: Varies with bitrate (16k = fair, 40k = very good)

**Bitrate Variants:**

| Variant | Bitrate | Bits/Sample | Payload Type | Quality | Use Case |
|---------|---------|-------------|--------------|---------|----------|
| G.726-16 | 16 kbit/s | 2 bits | 112 (dynamic) | Fair | Maximum compression |
| G.726-24 | 24 kbit/s | 3 bits | 113 (dynamic) | Good | Balanced compression |
| G.726-32 | 32 kbit/s | 4 bits | 2 (static) | Good | Most common, G.721 compatible |
| G.726-40 | 40 kbit/s | 5 bits | 114 (dynamic) | Very Good | Lower compression, better quality |

**Note:** G.726-32 is also known as G.721 and is the most widely supported variant.

## Configuration

### Enable Codecs in config.yml

```yaml
codecs:
  # G.729 Configuration
  g729:
    enabled: true      # Enable G.729 support
    variant: G729AB    # Options: G729, G729A, G729B, G729AB
  
  # G.726 Configuration  
  g726:
    enabled: true
    bitrate: 32000     # Options: 16000, 24000, 32000, 40000 (bits per second)
```

### Configuration Options

**G.729 Settings:**
- `enabled`: Enable/disable G.729 codec (true/false)
- `variant`: Which G.729 variant to use
  - `G729`: Base variant (no VAD/CNG)
  - `G729A`: Simplified variant (most common)
  - `G729B`: Base with VAD/CNG
  - `G729AB`: Simplified with VAD/CNG (recommended)

**G.726 Settings:**
- `enabled`: Enable/disable G.726 codec (true/false)
- `bitrate`: Default bitrate in bits per second
  - `16000`: 16 kbit/s (maximum compression)
  - `24000`: 24 kbit/s (balanced)
  - `32000`: 32 kbit/s (recommended, most compatible)
  - `40000`: 40 kbit/s (best quality)

## SDP Negotiation

### Codec Priority Order

The default codec negotiation order is:
1. PCMU (G.711 μ-law) - Payload Type 0
2. PCMA (G.711 A-law) - Payload Type 8
3. G.722 (HD Audio) - Payload Type 9
4. **G.729** - Payload Type 18
5. **G.726-32** - Payload Type 2
6. telephone-event (DTMF) - Payload Type 101

### SDP Example

When enabled, the PBX will advertise these codecs in SDP offers:

```
m=audio 10000 RTP/AVP 0 8 9 18 2 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:9 G722/8000
a=rtpmap:18 G729/8000
a=rtpmap:2 G726-32/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=sendrecv
```

### G.726 Variants in SDP

For non-standard G.726 bitrates, dynamic payload types are used:

```
m=audio 10000 RTP/AVP 0 112 113 114 101
a=rtpmap:0 PCMU/8000
a=rtpmap:112 G726-16/8000
a=rtpmap:113 G726-24/8000
a=rtpmap:114 G726-40/8000
a=rtpmap:101 telephone-event/8000
```

## Phone Configuration

### Supported Phones

The following phone templates have been updated to support G.729 and G.726:

- **Zultys ZIP33G**: Supports G.729 and G.726-32
- **Zultys ZIP37G**: Supports G.729 and G.726-32
- **Yealink T46S**: Supports G.729 and G.726-32
- **Yealink T28G**: Supports G.729 and G.726-32
- **Polycom VVX**: Check phone capabilities
- **Grandstream GXP**: Check phone capabilities

### Provisioning Templates

Phone provisioning templates automatically include the new codecs:

**Zultys Phones:**
```
account.1.codec.4.enable = 1
account.1.codec.4.payload_type = 18
account.1.codec.4.priority = 4
account.1.codec.4.name = G729

account.1.codec.5.enable = 1
account.1.codec.5.payload_type = 2
account.1.codec.5.priority = 5
account.1.codec.5.name = G726-32
```

**Yealink Phones:**
```
account.1.codec.4.enable = 1
account.1.codec.4.payload_type = G729
account.1.codec.5.enable = 1
account.1.codec.5.payload_type = G726-32
```

## Implementation Status

### G.729 Implementation

**Status**: Framework implementation (codec negotiation only)

The G.729 codec module provides:
- ✅ SDP negotiation and codec advertisement
- ✅ RTP payload type handling
- ✅ Variant selection (G729, G729A, G729B, G729AB)
- ❌ Actual encoding/decoding (requires codec library)

**To enable full encoding/decoding:**
1. Install a G.729 codec library:
   - `bcg729` (open-source, LGPL)
   - Intel IPP codec
   - Sipro/Broadcom codec
2. Integrate the library with `pbx/features/g729_codec.py`
3. Update the `encode()` and `decode()` methods

### G.726 Implementation

**Status**: Partial implementation

The G.726 codec module provides:
- ✅ SDP negotiation for all variants
- ✅ RTP payload type handling
- ✅ **Full G.726-32 support** via Python's `audioop` module
- ⚠️ Framework-only support for G.726-16, G.726-24, G.726-40

**G.726-32 is production-ready** and can encode/decode audio using Python's built-in `audioop` module.

For G.726 variants (16/24/40 kbit/s), the system will:
- Negotiate the codec properly in SDP
- Advertise support to phones
- Require additional library integration for actual transcoding

## Bandwidth Comparison

| Codec | Bitrate | Bandwidth per Call | Quality | Compression |
|-------|---------|-------------------|---------|-------------|
| G.711 (PCMU/PCMA) | 64 kbit/s | ~87 kbit/s | Excellent | 1:1 |
| G.722 | 64 kbit/s | ~87 kbit/s | Excellent (HD) | 1:1 |
| G.726-40 | 40 kbit/s | ~63 kbit/s | Very Good | 1.6:1 |
| G.726-32 | 32 kbit/s | ~55 kbit/s | Good | 2:1 |
| G.726-24 | 24 kbit/s | ~47 kbit/s | Good | 2.7:1 |
| **G.729** | **8 kbit/s** | **~31 kbit/s** | **Good** | **8:1** |
| G.726-16 | 16 kbit/s | ~39 kbit/s | Fair | 4:1 |

*Note: Bandwidth includes RTP/UDP/IP overhead (~23 kbit/s)*

## When to Use Each Codec

### G.711 (PCMU/PCMA) - Default Choice
- **Use when**: You have adequate bandwidth and want best quality
- **Bandwidth**: 87 kbit/s per call
- **Quality**: Excellent (toll quality)
- **Compatibility**: Universal support
- **Latency**: Very low

### G.722 - High Quality
- **Use when**: You want HD audio with good bandwidth
- **Bandwidth**: 87 kbit/s per call
- **Quality**: Excellent (wideband/HD)
- **Compatibility**: Most modern phones
- **Latency**: Very low

### G.729 - Bandwidth Constrained
- **Use when**: Bandwidth is limited or expensive
- **Bandwidth**: 31 kbit/s per call (64% savings vs G.711)
- **Quality**: Good (near toll quality)
- **Compatibility**: Common in VoIP equipment
- **Latency**: Low
- **Best for**: Satellite links, slow DSL, cellular, international calls

### G.726-32 - Balanced Choice
- **Use when**: You want moderate compression with good quality
- **Bandwidth**: 55 kbit/s per call (37% savings vs G.711)
- **Quality**: Good
- **Compatibility**: Good (older equipment often supports this)
- **Latency**: Very low
- **Best for**: Legacy system compatibility, moderate bandwidth savings

### G.726-40 - Quality Priority
- **Use when**: You want slight compression with very good quality
- **Bandwidth**: 63 kbit/s per call (28% savings vs G.711)
- **Quality**: Very Good
- **Best for**: Slight bandwidth savings while maintaining high quality

### G.726-24 - Compression Priority
- **Use when**: You need more compression than G.726-32
- **Bandwidth**: 47 kbit/s per call (46% savings vs G.711)
- **Quality**: Good
- **Best for**: Moderate bandwidth constraints

### G.726-16 - Maximum Compression
- **Use when**: You need maximum ADPCM compression
- **Bandwidth**: 39 kbit/s per call (55% savings vs G.711)
- **Quality**: Fair
- **Best for**: Extreme bandwidth constraints (but G.729 is better)

## Testing

### Run Codec Tests

```bash
# Test all new codec functionality
python -m unittest tests/test_g729_g726_codecs.py -v

# Test SDP generation
python -m unittest tests.test_g729_g726_codecs.TestSDPWithNewCodecs -v

# Test G.729 codec
python -m unittest tests.test_g729_g726_codecs.TestG729Codec -v

# Test G.726 codec
python -m unittest tests.test_g729_g726_codecs.TestG726Codec -v
```

### Verify SDP Advertisement

1. Start the PBX with codecs enabled
2. Make a test call
3. Check SDP in SIP INVITE message:
   ```
   m=audio 10000 RTP/AVP 0 8 9 18 2 101
   a=rtpmap:18 G729/8000
   a=rtpmap:2 G726-32/8000
   ```

### Test Call Quality

When testing codec quality:
1. Set up test calls with each codec
2. Verify audio quality
3. Monitor bandwidth usage
4. Check for packet loss tolerance
5. Test with various network conditions

## Troubleshooting

### G.729 Issues

**Problem**: G.729 negotiated but no audio
- **Cause**: Codec library not installed
- **Solution**: G.729 encoding/decoding requires external library. System will negotiate but cannot transcode. Install bcg729 or equivalent.

**Problem**: Phone doesn't support G.729
- **Cause**: Phone firmware or license issue
- **Solution**: Check phone capabilities. Some phones require G.729 license upgrade.

### G.726 Issues

**Problem**: G.726-32 negotiated but distorted audio
- **Cause**: Phone using wrong ADPCM variant
- **Solution**: Ensure phone is using ITU G.726, not other ADPCM variants

**Problem**: G.726-24/16/40 no audio
- **Cause**: Only G.726-32 fully implemented
- **Solution**: Use G.726-32 for now, or integrate additional codec library

### General Codec Issues

**Problem**: Codec not appearing in SDP
- **Cause**: Codec disabled in config
- **Solution**: Check `config.yml` and ensure codec is enabled

**Problem**: One-way audio with new codec
- **Cause**: NAT/firewall or codec mismatch
- **Solution**: Check RTP ports, verify both endpoints support the codec

## API Usage

### Using G.729 Programmatically

```python
from pbx.features.g729_codec import G729Codec, G729CodecManager

# Initialize codec
codec = G729Codec(variant='G729AB')

# Get codec info
info = codec.get_info()
print(f"Codec: {info['name']}, Bitrate: {info['bitrate']}")

# Get SDP description
sdp_line = codec.get_sdp_description()
print(sdp_line)  # "rtpmap:18 G729/8000"

# Use codec manager
config = {'codecs.g729.enabled': True, 'codecs.g729.variant': 'G729AB'}
manager = G729CodecManager(config)

# Create encoder/decoder for a call
encoder = manager.create_encoder('call-12345')
decoder = manager.create_decoder('call-12345')

# Cleanup when call ends
manager.release_codec('call-12345')
```

### Using G.726 Programmatically

```python
from pbx.features.g726_codec import G726Codec, G726CodecManager

# Initialize G.726-32 codec
codec = G726Codec(bitrate=32000)

# Encode PCM to G.726-32 (works!)
pcm_data = b'...'  # 16-bit PCM audio
g726_data = codec.encode(pcm_data)

# Decode G.726-32 to PCM
decoded_pcm = codec.decode(g726_data)

# Use different bitrate (framework only)
codec_40k = G726Codec(bitrate=40000)
print(codec_40k.get_info())
```

## Production Deployment

### Recommendations

1. **Start with G.711 and G.722** - Keep these as primary codecs
2. **Add G.729 for bandwidth savings** - Enable when needed for constrained networks
3. **Use G.726-32 for legacy compatibility** - Good middle ground
4. **Monitor call quality** - Watch MOS scores when using compressed codecs
5. **Test before production** - Verify all phones support chosen codecs

### Codec Selection Strategy

**For Maximum Compatibility:**
```yaml
codecs:
  g722: {enabled: true}
  g729: {enabled: false}
  g726: {enabled: false}
```

**For Bandwidth Optimization:**
```yaml
codecs:
  g722: {enabled: true}
  g729: {enabled: true, variant: G729AB}
  g726: {enabled: true, bitrate: 32000}
```

**For Legacy Support:**
```yaml
codecs:
  g722: {enabled: false}  # Some old phones don't support
  g729: {enabled: false}
  g726: {enabled: true, bitrate: 32000}
```

## References

- [RFC 3551 - RTP Profile for Audio and Video Conferences](https://tools.ietf.org/html/rfc3551)
- [ITU-T G.729 Specification](https://www.itu.int/rec/T-REC-G.729)
- [ITU-T G.726 Specification](https://www.itu.int/rec/T-REC-G.726)
- [RFC 3952 - RTP Payload Format for ITU-T G.726](https://tools.ietf.org/html/rfc3952)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 12, 2024 | Initial G.729 and G.726 support implementation |

## Support

For issues or questions:
1. Check this guide first
2. Review test cases in `tests/test_g729_g726_codecs.py`
3. Check SDP negotiation logs
4. Verify phone codec capabilities

---

**Note**: This implementation provides framework support for codec negotiation. For production use with actual audio encoding/decoding, integrate appropriate codec libraries.
