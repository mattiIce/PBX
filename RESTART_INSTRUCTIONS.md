# RESTART REQUIRED FOR QoS FIX

## Summary of Issue
The QoS monitoring was sampling every 10th RTP packet, causing approximately 90% packet loss to be incorrectly reported. Your recent call showed:
- **89.87% packet loss** (FALSE - this is the sampling artifact)
- **1.00 MOS score** (Bad) - directly caused by the false packet loss

## What Was Fixed
1. ✅ RTP handler now tracks **ALL packets** instead of every 10th packet
2. ✅ MOS calculation now runs at call end to ensure a score is always computed
3. ✅ Added diagnostic tool to help troubleshoot future QoS issues

## Restart Instructions

### Option 1: Restart PBX Service (Recommended)
```bash
# If running as systemd service
sudo systemctl restart pbx

# Or if using specific service name
sudo systemctl restart pbx.service
```

### Option 2: Restart Manually
```bash
# Find the PBX process
ps aux | grep main.py

# Kill the process
sudo kill <PID>

# Start PBX again
cd /path/to/PBX
python main.py
```

### Option 3: Restart in Docker
```bash
# If running in Docker
docker restart pbx-container

# Or restart docker-compose
docker-compose restart
```

## Verification After Restart

### Step 1: Make a Test Call
Make a test call that lasts at least 30 seconds.

### Step 2: Check QoS Metrics
Navigate to the Admin Panel → Call Quality tab and check the recent call history.

### Expected Results After Fix:
- ✅ Packet loss should be **< 5%** for good network conditions (not 89%)
- ✅ MOS score should be **> 4.0** for good quality calls (not 1.0)
- ✅ Jitter should be measured (typically 10-30ms)
- ⚠️  Latency will still be 0.0 (RTCP not yet implemented - this is normal)

### Step 3: Use Diagnostic Tool (Optional)
If you still see issues, run the diagnostic tool:

```bash
cd /path/to/PBX
python scripts/diagnose_qos.py "CALL_ID"
```

Example:
```bash
python scripts/diagnose_qos.py "0_2378921583@192.168.10.133"
```

## Expected Improvements

### Before Fix:
```
Call ID: 0_2378921583@192.168.10.133
Duration: 16.76s
MOS: 1.00 (Bad)
Packet Loss: 89.87% ❌ FALSE
Jitter: 0.1ms
Latency: 0.0ms
```

### After Fix:
```
Call ID: [new call]
Duration: 16.76s
MOS: 4.3+ (Excellent) ✅
Packet Loss: < 1% ✅
Jitter: 10-30ms (normal) ✅
Latency: 0.0ms (RTCP not implemented yet)
```

## Known Limitations

### Latency Always 0.0
- **This is NORMAL** - Latency measurement requires RTCP support
- RTCP implementation is a future enhancement
- MOS scores are calculated using jitter and packet loss only
- This does not affect call quality, only the displayed metric

## Troubleshooting

### If packet loss is still high after restart:
1. Run the diagnostic tool: `python scripts/diagnose_qos.py "CALL_ID"`
2. Check network conditions with: `tcpdump -i any -n 'udp portrange 10000-20000'`
3. Verify firewall rules allow RTP traffic
4. Check for actual network congestion or WiFi issues

### If MOS is still 0.0:
- This means **no RTP packets were received**
- Check firewall rules for incoming RTP (ports 10000-20000)
- Verify NAT traversal is working correctly
- Run diagnostic tool for specific recommendations

## Need Help?
Check the logs for QoS-related messages:
```bash
grep -i "qos\|mos\|packet" /var/log/pbx/pbx.log
```

Or run with debug logging:
```bash
# Set log level to DEBUG in config.yml
logging:
  level: DEBUG
```
