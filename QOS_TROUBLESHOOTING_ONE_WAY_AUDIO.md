# QoS Troubleshooting: One-Way Audio Issues

## Date
December 11, 2025

## Overview

This guide helps you interpret QoS (Quality of Service) metrics to diagnose and fix one-way audio problems in VoIP calls. One-way audio occurs when callers can hear each other in only one direction.

## Understanding Bidirectional QoS Metrics

### What Are Bidirectional Metrics?

Each call is monitored in **two separate directions**:
- **A→B (a_to_b)**: Audio flowing from endpoint A to endpoint B
- **B→A (b_to_a)**: Audio flowing from endpoint B to endpoint A

This separation is crucial because RTP (Real-time Transport Protocol) streams are independent in each direction, and audio issues often affect only one direction.

### Example QoS Output

```
Call ID                                    Start Time              Duration  MOS    Quality      Loss%   Jitter  Latency
0_4279726476@192.168.10.133_a_to_b        12/11/2025, 12:30:49 PM 25.05s    0.00   Bad          0.00%   0.0     0.0
0_4279726476@192.168.10.133_b_to_a        12/11/2025, 12:30:49 PM 25.05s    4.41   Excellent    0.00%   0.1     0.0
```

## Interpreting the Metrics

### What Each Metric Means

| Metric | Description | Normal Range | Problem Indicator |
|--------|-------------|--------------|-------------------|
| **MOS Score** | Mean Opinion Score (call quality) | 4.0-5.0 | < 3.5 (or 0.00 = no audio) |
| **Quality** | Human-readable quality rating | Excellent/Good | Bad, Poor, or "Bad" with MOS 0.00 |
| **Loss %** | Percentage of lost RTP packets | < 1% | > 2% |
| **Jitter** | Variation in packet arrival (ms) | < 30ms | > 50ms |
| **Latency** | Round-trip delay (ms) | < 150ms | > 300ms |

### What MOS 0.00 Means

A **MOS score of 0.00** indicates:
- ❌ **No RTP packets were received** in that direction
- ❌ The endpoint is **not sending audio** OR audio is **being blocked**
- ✅ This is a definitive indicator of one-way audio

## Diagnosing the Problem

### Example Analysis

Looking at the example above:

```
A→B: MOS 0.00 (Bad)    ← ⚠️ NO AUDIO THIS DIRECTION
B→A: MOS 4.41 (Excellent) ← ✅ Audio working fine
```

**Diagnosis**: One-way audio issue. Audio is only flowing from B to A.

**What This Means**:
- Endpoint B can hear endpoint A ✅
- Endpoint A **cannot** hear endpoint B ❌

### Common Patterns

#### Pattern 1: Complete One-Way Audio
```
A→B: MOS 0.00, Loss 0.00%, Jitter 0.0, Latency 0.0  ← No packets received
B→A: MOS 4.41, Loss 0.00%, Jitter 0.1, Latency 0.0  ← Normal audio
```
**Issue**: Endpoint B is not sending RTP, or packets are being blocked

#### Pattern 2: Both Directions Dead
```
A→B: MOS 0.00, Loss 0.00%, Jitter 0.0, Latency 0.0  ← No packets
B→A: MOS 0.00, Loss 0.00%, Jitter 0.0, Latency 0.0  ← No packets
```
**Issue**: No RTP flowing in either direction - signaling problem or both endpoints blocked

#### Pattern 3: Asymmetric Quality
```
A→B: MOS 4.35, Loss 0.5%, Jitter 12.3, Latency 85.0  ← Good quality
B→A: MOS 3.2,  Loss 8.2%, Jitter 67.8, Latency 220.0 ← Poor quality
```
**Issue**: Network path quality differs by direction - routing or congestion issue

## Root Causes and Solutions

### 1. Firewall/NAT Issues (Most Common)

**Symptoms**:
- One direction works, other shows MOS 0.00
- RTP packets blocked by firewall

**Solution**:
```bash
# Check if RTP ports are open (UDP 10000-20000)
sudo iptables -L -n | grep 10000

# Allow RTP ports bidirectionally
sudo iptables -A INPUT -p udp --dport 10000:20000 -j ACCEPT
sudo iptables -A OUTPUT -p udp --sport 10000:20000 -j ACCEPT

# For firewalld
sudo firewall-cmd --permanent --add-port=10000-20000/udp
sudo firewall-cmd --reload
```

**Verification**:
```bash
# Capture RTP traffic while on a call
sudo tcpdump -n udp portrange 10000-20000

# You should see packets in BOTH directions:
# IP 192.168.10.100.12345 > 192.168.10.133.10000: UDP
# IP 192.168.10.133.10000 > 192.168.10.100.12345: UDP
```

### 2. Symmetric RTP Not Working

**Symptoms**:
- First few seconds work, then one direction stops
- PBX doesn't learn endpoint address correctly

**Solution**:
Check RTP handler logs:
```bash
grep "learned.*address" /var/log/pbx/pbx.log

# Should see entries like:
# Learned endpoint A address: 192.168.10.100:12345
# Learned endpoint B address: 192.168.10.133:54321
```

If addresses aren't being learned:
1. Check that endpoints are sending RTP early
2. Verify SDP in INVITE has correct addresses
3. Check for strict NAT that changes ports

### 3. Codec Negotiation Failure

**Symptoms**:
- Call connects but no audio
- Both directions show MOS 0.00

**Solution**:
```bash
# Check negotiated codec in logs
grep "codec" /var/log/pbx/pbx.log | grep <call_id>

# Verify endpoints support the codec
# Check SDP in SIP messages for codec mismatch
```

Common codec issues:
- One endpoint only supports G.729, other only supports G.711
- Sample rate mismatch (8kHz vs 16kHz)
- No common codec negotiated

### 4. Network Routing/Path Issues

**Symptoms**:
- Asymmetric quality (both directions work but different MOS)
- One direction has high loss/jitter

**Solution**:
```bash
# Trace route from PBX to endpoint
traceroute <endpoint_ip>

# Check for:
# - Different paths in each direction
# - High hop count (>15 hops)
# - Packet loss on specific router
```

### 5. Endpoint Not Sending RTP

**Symptoms**:
- One direction MOS 0.00
- No RTP packets visible in tcpdump from that endpoint

**Solution**:
1. **Check endpoint settings**: Verify RTP/audio is enabled
2. **Reboot endpoint**: May fix stuck audio state
3. **Check codec support**: Endpoint may not support negotiated codec
4. **Verify SIP registration**: Endpoint may not be properly registered

## Step-by-Step Troubleshooting

### Step 1: Identify the Problem Direction

Look at QoS metrics:
- If **A→B shows MOS 0.00**: Endpoint B is not receiving (or A is not sending)
- If **B→A shows MOS 0.00**: Endpoint A is not receiving (or B is not sending)

### Step 2: Verify RTP Traffic with tcpdump

```bash
# Start capture on RTP ports
sudo tcpdump -n -i any udp portrange 10000-20000

# Make a test call
# Observe output - you should see packets in BOTH directions

# Example of good output:
# 12:30:45.123 IP 192.168.10.100.12345 > 192.168.10.133.10500: UDP
# 12:30:45.143 IP 192.168.10.133.10500 > 192.168.10.100.12345: UDP
# 12:30:45.163 IP 192.168.10.100.12345 > 192.168.10.133.10500: UDP
```

**What to look for**:
- ✅ Packets flowing both directions = Firewall OK
- ❌ Packets only in one direction = Firewall/NAT blocking
- ❌ No packets at all = Routing problem or codec issue

### Step 3: Check Firewall Rules

```bash
# Linux iptables
sudo iptables -L -n -v | grep -E "10000|20000"

# Should show ACCEPT rules for UDP ports 10000-20000
# If not, add rules (see solution #1 above)
```

### Step 4: Verify Symmetric RTP Learning

```bash
# Check PBX logs for address learning
tail -f /var/log/pbx/pbx.log | grep -i "learned"

# During call setup, you should see:
# INFO: Learned endpoint A address from RTP: 192.168.10.100:12345
# INFO: Learned endpoint B address from RTP: 192.168.10.133:54321
```

If addresses aren't being learned:
```bash
# Check RTP handler configuration
grep -i "symmetric" config.yml

# Ensure symmetric_rtp is enabled:
# rtp:
#   symmetric_rtp: true
```

### Step 5: Check Call Logs

```bash
# Find the call in logs
grep "0_4279726476@192.168.10.133" /var/log/pbx/pbx.log

# Look for errors:
# - "Failed to relay RTP packet"
# - "No route to host"
# - "Permission denied"
# - "Codec negotiation failed"
```

### Step 6: Verify Endpoints Can Reach Each Other

```bash
# From PBX, ping both endpoints
ping 192.168.10.100
ping 192.168.10.133

# Check routing
ip route get 192.168.10.100
ip route get 192.168.10.133
```

## Quick Diagnostic Checklist

Use this checklist when you see MOS 0.00 in one direction:

- [ ] Firewall allows UDP 10000-20000 (both INPUT and OUTPUT)
- [ ] NAT configuration allows RTP pass-through
- [ ] Both endpoints can ping PBX and each other
- [ ] Symmetric RTP is enabled in PBX config
- [ ] RTP packets visible in tcpdump (both directions)
- [ ] Call logs show successful codec negotiation
- [ ] Endpoints support the negotiated codec
- [ ] No "Permission denied" or "Route to host" errors in logs
- [ ] PBX learned both endpoint addresses from RTP

## Using the Admin Panel

### Viewing QoS Metrics

1. Log into Admin Panel
2. Navigate to **Call Quality (QoS)** tab
3. Look at **Active Call Quality** or **Recent Call Quality History**

### What to Look For

The admin panel will now highlight one-way audio issues:

- 🟢 **Green/Blue rows**: Normal call quality
- 🟡 **Yellow rows**: Quality degradation warning
- 🔴 **Red highlighted rows**: One-way audio detected (MOS 0.00)
- ⚠️ **Warning icon**: Appears next to quality rating when audio is missing

### Diagnostic Alerts

When one-way audio is detected, the admin panel shows:

```
⚠️ One-Way Audio Issue - No audio A→B (only B→A working)

Troubleshooting:
1) Check firewall/NAT rules for RTP ports (10000-20000)
2) Verify symmetric RTP is working
3) Check endpoint is sending RTP packets
4) Verify network path with tcpdump
```

## Real-World Example Walkthrough

### Scenario

User reports: "I can hear the other person, but they can't hear me"

### QoS Data Shows

```
Call: 0_4279726476@192.168.10.133_a_to_b
Duration: 25.05s
MOS: 0.00 (Bad)
Packet Loss: 0.00%
Jitter: 0.0ms
Latency: 0.0ms

Call: 0_4279726476@192.168.10.133_b_to_a
Duration: 25.05s
MOS: 4.41 (Excellent)
Packet Loss: 0.00%
Jitter: 0.1ms
Latency: 0.0ms
```

### Analysis

1. **B→A works perfectly** (MOS 4.41) - Endpoint A is receiving audio from B
2. **A→B has no audio** (MOS 0.00) - Endpoint B is not receiving audio from A

This means:
- 👤 **Caller A**: Can hear B ✅, but B can't hear A ❌
- 👤 **Caller B**: Cannot hear A ❌, but A can hear B ✅

### Investigation

```bash
# Step 1: Check if RTP is leaving A
sudo tcpdump -n -i any src 192.168.10.100 and udp portrange 10000-20000

# If packets visible: Audio is leaving A → Firewall/routing issue
# If no packets: Endpoint A problem (not sending RTP)
```

Let's say packets ARE visible from A...

```bash
# Step 2: Check if packets reach PBX
sudo tcpdump -n -i eth0 src 192.168.10.100 and dst port 10000:20000

# If visible: PBX receiving but not forwarding
# If not visible: Firewall blocking inbound RTP
```

Let's say packets DO reach PBX...

```bash
# Step 3: Check if PBX forwards to B
sudo tcpdump -n -i eth0 dst 192.168.10.133 and udp portrange 10000-20000

# If not visible: RTP relay issue or address learning problem
```

### Solution Found

In this case, checking logs revealed:
```
ERROR: Cannot relay RTP to endpoint B - address not yet learned
```

**Root cause**: Endpoint B never sent initial RTP, so PBX doesn't know where to send audio

**Fix**:
```bash
# Option 1: Configure B to send early media
# (vendor-specific - check phone documentation)

# Option 2: Use late-offer SDP to force B to send first
# (in config.yml)
# sip:
#   late_offer_enabled: true

# Option 3: Restart call - sometimes fixes stuck state
```

## Prevention

### Best Practices

1. **Always use symmetric RTP** (enabled by default)
2. **Open RTP ports bidirectionally** in firewall
3. **Monitor QoS metrics** regularly to catch issues early
4. **Set up alerts** for MOS < 3.5 (see Admin Panel → QoS → Alert Thresholds)
5. **Test calls** after any network changes

### Monitoring

Set up automated monitoring:

```bash
# Check QoS API every 5 minutes
*/5 * * * * curl -s http://localhost:8080/api/qos/alerts | grep -q '"count":0' || echo "QoS alerts detected!"

# Get active call quality
curl http://localhost:8080/api/qos/metrics | jq '.metrics[] | select(.mos_score < 1.0)'
```

### Network Configuration

Recommended firewall rules:

```bash
# INPUT chain - allow RTP from anywhere
iptables -A INPUT -p udp --dport 10000:20000 -j ACCEPT

# OUTPUT chain - allow RTP to anywhere
iptables -A OUTPUT -p udp --sport 10000:20000 -j ACCEPT

# If using connection tracking
iptables -A INPUT -p udp --dport 10000:20000 -m state --state RELATED,ESTABLISHED -j ACCEPT
```

## FAQs

### Q: Why is latency always 0.0?

**A**: RTCP (which measures latency) is not yet implemented. This is normal and doesn't affect packet loss or jitter measurements.

### Q: Can I have good quality in one direction but poor in the other?

**A**: Yes! Network paths are often asymmetric. You might see:
- A→B: MOS 4.3 (direct route, low latency)
- B→A: MOS 3.5 (congested route, packet loss)

This indicates a routing or network quality issue.

### Q: What if both directions show MOS 0.00?

**A**: This indicates no RTP is flowing at all. Check:
1. SIP call was established (check signaling)
2. Codec negotiation succeeded
3. Both endpoints support the negotiated codec
4. Firewall isn't blocking all RTP

### Q: How can I see this data in real-time?

**A**: Use the Admin Panel:
1. Go to **Call Quality (QoS)** tab
2. Click **🔄 Refresh Metrics**
3. View **Active Call Quality** section

Or use the API:
```bash
watch -n 5 'curl -s http://localhost:8080/api/qos/metrics | jq'
```

## References

- [QoS Monitoring Guide](QOS_MONITORING_GUIDE.md) - Complete QoS system documentation
- [Bidirectional RTP Fix](BIDIRECTIONAL_RTP_PACKET_LOSS_FIX.md) - Technical details on bidirectional tracking
- [RTP Handler Documentation](pbx/rtp/handler.py) - Source code reference
- [ITU-T G.107](https://www.itu.int/rec/T-REC-G.107) - E-Model for MOS calculation
- [RFC 3550](https://tools.ietf.org/html/rfc3550) - RTP specification

## Support

If you continue to experience one-way audio after following this guide:

1. **Capture diagnostic data**:
   ```bash
   # Call logs
   grep <call_id> /var/log/pbx/pbx.log > call-debug.log
   
   # RTP packet capture (30 seconds during call)
   timeout 30 sudo tcpdump -w rtp-capture.pcap udp portrange 10000-20000
   
   # QoS metrics
   curl http://localhost:8080/api/qos/call/<call_id> > qos-data.json
   ```

2. **Open a GitHub issue** with:
   - QoS metrics showing the problem
   - Call logs (call-debug.log)
   - Network topology diagram
   - Steps to reproduce

3. **Include environment info**:
   - PBX version
   - Endpoint types/models
   - Network setup (NAT, firewall, routers)
   - Operating system

---

**Version**: 1.0  
**Last Updated**: December 11, 2025  
**Status**: ✅ Production Ready  
**Applies to**: PBX v1.0+  

**Built to help troubleshoot real VoIP issues** 🎯
