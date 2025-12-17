# Comprehensive Codec Comparison Guide

**Date**: December 17, 2024  
**Version**: 1.0

## Overview

This guide provides a comprehensive comparison of all audio codecs supported by the PBX system, helping you make informed decisions about codec selection for different scenarios.

## Supported Codecs Summary

| Codec | Status | Bitrate | Sample Rate | Quality (MOS) | License | Best For |
|-------|--------|---------|-------------|---------------|---------|----------|
| **G.711 (PCMU/PCMA)** | ✅ Full | 64 kbps | 8 kHz | 4.1 | Free | Maximum compatibility, reliability |
| **G.722** | ✅ Full | 64 kbps | 16 kHz | 4.3-4.5 | Free | HD voice, wideband audio |
| **Opus** | ✅ Full | 6-510 kbps | 8-48 kHz | 4.2-4.7 | BSD | Modern VoIP, adaptive bitrate |
| **iLBC** | ✅ Framework | 13.33-15.2 kbps | 8 kHz | 3.8-4.0 | Free | Packet loss resilience |
| **Speex** | ✅ Framework | 2.15-44 kbps | 8-32 kHz | 3.6-4.3 | BSD | Open source alternative |
| **G.729** | ⚙️ Framework | 8 kbps | 8 kHz | 3.9 | Licensed | Low bandwidth |
| **G.726-32** | ✅ Partial | 32 kbps | 8 kHz | 3.8 | Free | Legacy compatibility |

## Detailed Codec Comparison

### G.711 (PCMU/PCMA) - The Reliable Standard

**Specifications**:
- Bitrate: 64 kbps
- Sample Rate: 8 kHz (narrowband)
- Compression: None (PCM)
- Latency: <1 ms (algorithmic)
- MOS: 4.1 (toll quality)

**Variants**:
- **PCMU (μ-law)**: Used in North America, Japan
- **PCMA (A-law)**: Used in Europe, rest of world

**Pros**:
- ✅ Universal compatibility
- ✅ Excellent audio quality
- ✅ No compression artifacts
- ✅ Zero computational overhead
- ✅ Lowest latency

**Cons**:
- ❌ High bandwidth usage (64 kbps)
- ❌ No packet loss concealment
- ❌ Narrowband only (8 kHz)

**Best For**: Default choice when bandwidth is adequate

**When to Use**:
- LAN deployments with ample bandwidth
- Maximum compatibility required
- Lowest latency needed
- Simple,reliable voice calls

---

### G.722 - HD Voice Quality

**Specifications**:
- Bitrate: 64 kbps
- Sample Rate: 16 kHz (wideband)
- Compression: SB-ADPCM
- Latency: ~20-40 ms
- MOS: 4.3-4.5

**Pros**:
- ✅ HD voice quality (wideband)
- ✅ Same bandwidth as G.711
- ✅ Wide phone support
- ✅ Low latency
- ✅ Better speech clarity

**Cons**:
- ❌ Higher CPU than G.711
- ❌ Still 64 kbps bandwidth
- ❌ Limited to 16 kHz

**Best For**: HD voice without increasing bandwidth

**When to Use**:
- Want better quality than G.711
- Bandwidth allows 64 kbps
- Modern phones available
- Conference calls

---

### Opus - The Modern Choice

**Specifications**:
- Bitrate: 6-510 kbps (adaptive)
- Sample Rate: 8-48 kHz (fullband)
- Compression: SILK + CELT hybrid
- Latency: 5-60 ms (configurable)
- MOS: 4.2-4.7 (bitrate dependent)

**Pros**:
- ✅ Adaptive bitrate
- ✅ Excellent quality at all bitrates
- ✅ Low latency
- ✅ Built-in packet loss concealment
- ✅ Forward error correction (FEC)
- ✅ Supports speech and music
- ✅ Full patent-free

**Cons**:
- ❌ Not supported by all phones
- ❌ Higher CPU than G.711
- ❌ Relatively new (less deployed)

**Best For**: Modern VoIP systems prioritizing quality and efficiency

**When to Use**:
- Modern deployment
- Variable network conditions
- Need bandwidth flexibility
- Packet loss is a concern
- Music or HD voice needed

---

### iLBC - Packet Loss Champion

**Specifications**:
- Bitrate: 13.33 kbps (30ms) or 15.2 kbps (20ms)
- Sample Rate: 8 kHz (narrowband)
- Compression: Block-independent coding
- Latency: 20-30 ms
- MOS: 3.8-4.0

**Pros**:
- ✅ Excellent packet loss concealment
- ✅ Royalty-free
- ✅ Low bandwidth
- ✅ Low computational cost
- ✅ Built-in PLC

**Cons**:
- ❌ Narrowband only (8 kHz)
- ❌ Lower quality than G.711
- ❌ Not universal phone support

**Best For**: Unreliable networks with packet loss

**When to Use**:
- Wireless/mobile scenarios
- Satellite links
- Poor network quality
- 1-10% packet loss expected
- Bandwidth limited but not extreme

---

### Speex - The Flexible Alternative

**Specifications**:
- Bitrate: 2.15-44 kbps (variable)
- Sample Rate: 8/16/32 kHz (selectable)
- Compression: CELP-based
- Latency: 20-30 ms
- MOS: 3.6-4.3 (mode/quality dependent)

**Modes**:
- Narrowband: 8 kHz, 2.15-24.6 kbps
- Wideband: 16 kHz, 3.95-42.2 kbps
- Ultra-wideband: 32 kHz, 4.15-44 kbps

**Pros**:
- ✅ Open source (BSD)
- ✅ Multiple bandwidth modes
- ✅ Variable bitrate
- ✅ Voice activity detection
- ✅ Quality configurable (0-10)

**Cons**:
- ❌ Being superseded by Opus
- ❌ Inconsistent phone support
- ❌ Lower quality than Opus

**Best For**: Legacy systems or when Opus unavailable

**When to Use**:
- Open source requirement
- Opus not supported
- Need bandwidth flexibility
- Working with older systems
- Note: Prefer Opus for new deployments

---

### G.729 - Maximum Compression

**Specifications**:
- Bitrate: 8 kbps
- Sample Rate: 8 kHz (narrowband)
- Compression: CS-ACELP
- Latency: ~25 ms
- MOS: 3.9

**Pros**:
- ✅ Very low bandwidth (8 kbps)
- ✅ Good quality for bitrate
- ✅ Wide VoIP support
- ✅ Proven technology

**Cons**:
- ❌ May require licensing
- ❌ Higher CPU than G.711
- ❌ Narrowband only
- ❌ No built-in PLC

**Best For**: Severely bandwidth-constrained scenarios

**When to Use**:
- Bandwidth extremely limited
- Many simultaneous calls
- International/satellite links
- Licensing acceptable

**Note**: Check licensing requirements for your jurisdiction

---

### G.726-32 - The Middle Ground

**Specifications**:
- Bitrate: 32 kbps
- Sample Rate: 8 kHz (narrowband)
- Compression: ADPCM
- Latency: <5 ms
- MOS: 3.8

**Pros**:
- ✅ 50% bandwidth of G.711
- ✅ Low latency
- ✅ Low complexity
- ✅ Legacy support

**Cons**:
- ❌ Lower quality than G.711
- ❌ No significant advantages over newer codecs
- ❌ Narrowband only

**Best For**: Legacy system compatibility

**When to Use**:
- Moderate bandwidth savings needed
- Legacy equipment requires it
- Simple ADPCM support
- Note: Consider Opus or iLBC instead

---

## Codec Selection Matrix

### By Network Condition

| Network Quality | Packet Loss | Bandwidth | Recommended Codecs |
|----------------|-------------|-----------|-------------------|
| **Excellent** | <0.1% | High | G.711, G.722, Opus (48kHz) |
| **Good** | 0.1-1% | Medium | Opus (32kbps), G.722, G.711 |
| **Fair** | 1-5% | Medium | Opus (24kbps), iLBC, Speex |
| **Poor** | 5-10% | Limited | iLBC, Opus (16kbps) |
| **Very Poor** | >10% | Very Limited | iLBC (30ms), G.729 |

### By Use Case

| Use Case | Primary | Secondary | Fallback |
|----------|---------|-----------|----------|
| **Office LAN** | G.711 | G.722 | Opus |
| **Remote Workers** | Opus | iLBC | Speex |
| **Mobile/Wireless** | iLBC | Opus | Speex |
| **International** | Opus | G.729 | iLBC |
| **Conference Rooms** | G.722 | Opus (48kHz) | G.711 |
| **Call Centers** | G.711 | Opus | G.722 |
| **Satellite Links** | iLBC | G.729 | Opus (low) |

### By Priority

| Priority | Codec | Reason |
|----------|-------|--------|
| **1. Compatibility** | G.711 | Universal support |
| **2. Quality** | G.722 | HD voice |
| **3. Packet Loss** | iLBC | Built-in PLC |
| **4. Open Source** | Speex | BSD license |
| **5. Low Bandwidth** | G.729 | 8 kbps |
| **6. Modern** | Opus | Best overall |

## Bandwidth Comparison

| Codec | Audio Bitrate | IP/UDP/RTP Overhead | Total Bandwidth | Calls per Mbps |
|-------|---------------|---------------------|-----------------|----------------|
| G.711 | 64 kbps | ~23 kbps | ~87 kbps | 11 |
| G.722 | 64 kbps | ~23 kbps | ~87 kbps | 11 |
| Opus (32k) | 32 kbps | ~23 kbps | ~55 kbps | 18 |
| iLBC (30ms) | 13.33 kbps | ~23 kbps | ~36 kbps | 27 |
| G.729 | 8 kbps | ~23 kbps | ~31 kbps | 32 |
| G.726-32 | 32 kbps | ~23 kbps | ~55 kbps | 18 |

## Quality vs. Bandwidth Chart

```
MOS Score
4.5 │                          ● Opus (48kHz)
4.4 │                     ● G.722
4.3 │                ●
4.2 │           ● Opus (32kHz)
4.1 │      ● G.711
4.0 │  ● iLBC          ● Speex WB
3.9 │     ● G.729
3.8 │          ● G.726-32
3.7 │               ● Speex NB
    └───┴───┴───┴───┴───┴───┴───┴───
    0   10  20  30  40  50  60  70  kbps
```

## Recommended Codec Priority Orders

### Default (Balanced)
```yaml
Priority Order: PCMU > PCMA > G722 > iLBC > Speex > G729 > G726-32
Codecs: [0, 8, 9, 97, 98, 18, 2]
```
- Prioritizes reliability (G.711)
- HD voice available (G.722)
- Packet loss protection (iLBC)
- Open source fallback (Speex)

### Modern (Quality-First)
```yaml
Priority Order: Opus > G722 > PCMU > PCMA > iLBC
Codecs: [111, 9, 0, 8, 97]
```
- Best quality (Opus)
- HD fallback (G.722)
- Reliability (G.711)

### Bandwidth-Optimized
```yaml
Priority Order: G729 > iLBC > Opus(low) > Speex > PCMU
Codecs: [18, 97, 111, 98, 0]
```
- Minimum bandwidth (G.729)
- Packet loss protection (iLBC)
- Flexibility (Opus)

### Maximum Compatibility
```yaml
Priority Order: PCMU > PCMA > G722 > G726-32
Codecs: [0, 8, 9, 2]
```
- Universal support
- No modern codecs
- Legacy friendly

## Performance Characteristics

### CPU Usage (Relative to G.711 = 1.0x)

| Codec | Encode | Decode | Notes |
|-------|--------|--------|-------|
| G.711 | 1.0x | 1.0x | Baseline (minimal CPU) |
| G.722 | 1.5x | 1.5x | Low overhead |
| iLBC | 1.5x | 1.5x | Low complexity |
| Speex NB | 2.0x | 2.0x | Configurable |
| G.729 | 3.0x | 3.0x | Higher complexity |
| Opus | 2.0-4.0x | 2.0-4.0x | Depends on complexity setting |
| G.726-32 | 1.2x | 1.2x | Very low |

### Latency Components

| Codec | Algorithmic | Frame Size | Typical Total |
|-------|-------------|------------|---------------|
| G.711 | <1 ms | 10-20 ms | 40-80 ms |
| G.722 | 20-40 ms | 10-20 ms | 60-100 ms |
| iLBC | 20-30 ms | 20-30 ms | 60-100 ms |
| Speex | 20-30 ms | 20 ms | 60-100 ms |
| G.729 | 25 ms | 10 ms | 65-105 ms |
| Opus | 5-60 ms | 10-60 ms | 40-150 ms |

*Total latency includes network propagation, jitter buffer, and codec delays*

## Deployment Recommendations

### Small Office (< 50 Users)
- **Primary**: G.711 (PCMU/PCMA)
- **Secondary**: G.722
- **Tertiary**: Opus
- **Rationale**: Ample LAN bandwidth, prioritize simplicity and quality

### Medium Business (50-500 Users)
- **Primary**: G.722
- **Secondary**: Opus
- **Tertiary**: G.711
- **Rationale**: Balance quality and bandwidth, HD voice preferred

### Large Enterprise (500+ Users)
- **Primary**: Opus
- **Secondary**: G.722
- **Tertiary**: iLBC, G.711
- **Rationale**: Optimize bandwidth, support varied network conditions

### Mobile/Remote Workers
- **Primary**: iLBC
- **Secondary**: Opus (adaptive)
- **Tertiary**: Speex
- **Rationale**: Handle packet loss, variable bandwidth

### Call Center
- **Primary**: G.711
- **Secondary**: G.722
- **Tertiary**: Opus
- **Rationale**: Maximize quality and reliability, high call volume

### International/WAN
- **Primary**: Opus (16-24 kbps)
- **Secondary**: iLBC
- **Tertiary**: G.729
- **Rationale**: Optimize bandwidth, handle latency and packet loss

## Configuration Examples

### Balanced Configuration (Recommended)
```yaml
codecs:
  # High quality, reliable
  g722:
    enabled: true
    bitrate: 64000
  
  # Modern, adaptive
  opus:
    enabled: true
    sample_rate: 48000
    bitrate: 32000
  
  # Packet loss protection
  ilbc:
    enabled: true
    mode: 30
  
  # Open source alternative
  speex:
    enabled: true
    mode: nb
    quality: 8
  
  # Low bandwidth
  g729:
    enabled: true
    variant: G729AB
```

## Testing Your Codec Selection

### Step 1: Define Requirements
- [ ] Maximum bandwidth per call?
- [ ] Network quality (packet loss %)?
- [ ] Quality expectations (MOS target)?
- [ ] Phone compatibility requirements?
- [ ] Licensing constraints?

### Step 2: Test Candidate Codecs
```bash
# Make test call with specific codec
# Monitor bandwidth, quality, CPU

# Test packet loss resilience
# Introduce 1-5% packet loss
# Compare audio quality

# Test multiple simultaneous calls
# Monitor system resources
```

### Step 3: Measure Performance
- Bandwidth utilization
- CPU usage
- MOS scores (subjective quality)
- Packet loss tolerance
- Call setup time

### Step 4: Deploy with Monitoring
- Start with conservative codec order
- Monitor call quality metrics
- Adjust based on real-world performance

## Troubleshooting

### Problem: Wrong codec being used

**Check SDP negotiation**:
```bash
# Review SIP INVITE/200 OK messages
# Verify m= line includes desired codecs
# Check a=rtpmap attributes
```

**Solution**: Adjust codec priority order

### Problem: One-way audio

**Common causes by codec**:
- G.711: NAT/firewall (not codec issue)
- Opus: Library not installed
- iLBC/Speex: Phone doesn't support codec

**Solution**: Check phone capabilities, verify codecs installed

### Problem: Poor quality despite good codec

**Check**:
- Network jitter and packet loss
- Jitter buffer settings
- CPU overload
- Wrong sample rate/bitrate

## Future Codec Support

### Potential Additions
- **AMR-WB**: Mobile telephony standard (patent concerns)
- **LC3**: Bluetooth LE audio codec
- **Lyra**: Google's ML-based codec

### Deprecations
- **G.726 variants (16/24/40)**: Use Opus instead
- **Standalone CELT/SILK**: Use Opus (includes both)

## Conclusion

**Key Recommendations**:

1. **For most deployments**: Use G.711 as default, G.722 for HD voice
2. **For modern systems**: Prioritize Opus over legacy codecs
3. **For poor networks**: Enable iLBC for packet loss protection
4. **For bandwidth optimization**: Use Opus with adaptive bitrate
5. **Always provide fallback**: Include G.711 for maximum compatibility

**Codec Selection Checklist**:
- ✅ Network quality assessed?
- ✅ Bandwidth budget determined?
- ✅ Phone compatibility verified?
- ✅ Quality targets defined?
- ✅ Licensing reviewed?
- ✅ Fallback codecs included?
- ✅ Testing plan in place?

---

**Version**: 1.0  
**Last Updated**: December 17, 2024

**Related Guides**:
- [G722_CODEC_GUIDE.md](G722_CODEC_GUIDE.md)
- [OPUS_CODEC_GUIDE.md](OPUS_CODEC_GUIDE.md)
- [ILBC_CODEC_GUIDE.md](ILBC_CODEC_GUIDE.md)
- [SPEEX_CODEC_GUIDE.md](SPEEX_CODEC_GUIDE.md)
- [G729_G726_CODEC_GUIDE.md](G729_G726_CODEC_GUIDE.md)

**Built with ❤️ for informed codec decisions**
