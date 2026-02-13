# Capacity Planning Guide

---

## Table of Contents

1. [Overview](#overview)
2. [Resource Requirements](#resource-requirements)
3. [Sizing Guidelines](#sizing-guidelines)
4. [Performance Metrics](#performance-metrics)
5. [Scaling Strategies](#scaling-strategies)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Cost Optimization](#cost-optimization)

---

## Overview

This guide helps you determine the appropriate infrastructure sizing for your PBX deployment based on:
- Number of concurrent calls
- Number of registered extensions
- Storage requirements
- Expected growth

### Quick Sizing Calculator

Use the calculator script to get initial sizing recommendations:

```bash
python3 scripts/capacity_calculator.py \
    --extensions 500 \
    --concurrent-calls 100 \
    --storage-days 90
```

---

## Resource Requirements

### CPU Requirements

**Per Concurrent Call:**
- ~0.02 CPU cores (G.711 codec)
- ~0.03 CPU cores (G.722 HD codec)
- ~0.05 CPU cores (Opus codec with FEC)

**Base System Overhead:**
- ~0.5 CPU cores (SIP processing, API, background tasks)

**Sizing Formula:**
```
Total CPU Cores = 0.5 + (Concurrent Calls × Codec Factor)
```

**Examples:**
```
Small (50 calls, G.711):   0.5 + (50 × 0.02) = 1.5 cores → 2 cores
Medium (200 calls, G.711): 0.5 + (200 × 0.02) = 4.5 cores → 6 cores
Large (500 calls, G.711):  0.5 + (500 × 0.02) = 10.5 cores → 12 cores
```

### Memory Requirements

**Per Extension:**
- ~2 MB per registered extension (SIP registration state)

**Per Call:**
- ~4 MB per active call (RTP buffers, call state)

**Database:**
- ~500 MB for PostgreSQL (small deployment)
- ~2 GB for PostgreSQL (medium deployment)
- ~4 GB for PostgreSQL (large deployment)

**Application:**
- ~1 GB base application memory

**Sizing Formula:**
```
Total RAM = 1 GB + (Extensions × 2 MB) + (Concurrent Calls × 4 MB) + Database RAM
```

**Examples:**
```
Small (100 ext, 25 calls):
  1 GB + (100 × 2 MB) + (25 × 4 MB) + 500 MB = 1.8 GB → 4 GB recommended

Medium (500 ext, 100 calls):
  1 GB + (500 × 2 MB) + (100 × 4 MB) + 2 GB = 4.4 GB → 8 GB recommended

Large (1000 ext, 200 calls):
  1 GB + (1000 × 2 MB) + (200 × 4 MB) + 4 GB = 7.8 GB → 16 GB recommended
```

### Network Bandwidth

**Per Call:**
- G.711 (PCMU/PCMA): ~87 Kbps (both directions)
- G.722 HD: ~87 Kbps (both directions)
- G.729: ~32 Kbps (both directions)
- Opus: ~40-128 Kbps (adaptive)

**Sizing Formula:**
```
Total Bandwidth (Mbps) = (Concurrent Calls × Codec Bandwidth) / 1000
```

**Examples:**
```
Small (50 calls, G.711):   50 × 87 Kbps = 4.35 Mbps → 10 Mbps recommended
Medium (200 calls, G.711): 200 × 87 Kbps = 17.4 Mbps → 25 Mbps recommended
Large (500 calls, G.711):  500 × 87 Kbps = 43.5 Mbps → 100 Mbps recommended
```

**Add 20-30% overhead for:**
- SIP signaling
- API traffic
- Admin interface
- Database replication (if HA)

### Storage Requirements

**Call Recordings:**
```
Storage (GB/month) = Concurrent Calls × Recording % × Avg Duration (min) × Codec Factor

Codec Factors:
- G.711: 0.66 MB per minute
- G.722: 0.66 MB per minute
- G.729: 0.24 MB per minute
```

**Example (200 concurrent calls, 50% recorded, 5 min avg):**
```
Storage = 200 × 0.5 × 5 × 0.66 MB = 330 MB per concurrent period
Monthly (30 days, 8 hours/day): ~80 GB
```

**Voicemail:**
```
Storage (GB/month) = Extensions × Messages/Day × Avg Length (sec) × Codec Factor

Typical: 500 ext × 3 msg/day × 60 sec × 0.011 MB/sec = ~1 GB/month
```

**Database:**
```
CDR: ~1 KB per call record
Extensions: ~5 KB per extension
Voicemail metadata: ~0.5 KB per message

Typical: 100K calls/month = 100 MB
```

**Total Storage Formula:**
```
Total Storage = Recordings + Voicemail + Database + OS (20 GB) + Growth (50%)

Example: (80 + 1 + 0.1 + 20) GB × 1.5 = ~152 GB → 200 GB recommended
```

---

## Sizing Guidelines

### Small Deployment (10-100 Users)

**Profile:**
- 10-100 extensions
- 10-25 concurrent calls
- Basic features

**Recommended Specs:**
```yaml
CPU: 2-4 cores
RAM: 4-8 GB
Disk: 100-200 GB SSD
Network: 10 Mbps
Database: PostgreSQL (local)
Deployment: Single VM or Docker
High Availability: Optional
```

**Monthly Costs (AWS):**
- t3.medium instance: ~$30
- EBS storage (100 GB): ~$10
- **Total: ~$40/month**

### Medium Deployment (100-500 Users)

**Profile:**
- 100-500 extensions
- 50-100 concurrent calls
- Full features + integrations
- Some call recording

**Recommended Specs:**
```yaml
CPU: 6-8 cores
RAM: 8-16 GB
Disk: 500 GB - 1 TB SSD
Network: 25-50 Mbps
Database: PostgreSQL (dedicated or RDS)
Deployment: Docker Compose or Kubernetes
High Availability: Recommended
```

**Monthly Costs (AWS):**
- 2× c5.2xlarge instances: ~$500
- RDS PostgreSQL (db.t3.large): ~$160
- EBS storage (1 TB): ~$100
- Load Balancer: ~$20
- **Total: ~$780/month**

### Large Deployment (500-1000+ Users)

**Profile:**
- 500-1000+ extensions
- 100-500+ concurrent calls
- Full features + enterprise integrations
- Extensive call recording
- Multi-site

**Recommended Specs:**
```yaml
CPU: 12-24 cores (per instance)
RAM: 16-32 GB (per instance)
Disk: 2-5 TB SSD
Network: 100+ Mbps
Database: PostgreSQL (HA cluster or RDS Multi-AZ)
Deployment: Kubernetes with auto-scaling
High Availability: Required
Geographic Redundancy: Recommended
```

**Monthly Costs (AWS):**
- 4× c5.4xlarge instances: ~$2,000
- RDS PostgreSQL Multi-AZ (db.m5.2xlarge): ~$800
- EBS storage (5 TB): ~$500
- Load Balancers (2): ~$40
- **Total: ~$3,340/month**

---

## Performance Metrics

### Target Metrics

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Call Setup Time | < 2 seconds | > 3 seconds |
| Call Success Rate | > 99% | < 95% |
| Voice Quality (MOS) | > 4.0 | < 3.5 |
| API Response Time (P95) | < 500ms | > 1000ms |
| SIP Registration Time | < 1 second | > 2 seconds |
| Jitter | < 30ms | > 50ms |
| Packet Loss | < 1% | > 2% |

### Benchmarking

Run performance benchmarks regularly:

```bash
# Benchmark call capacity
python3 scripts/load_test_sip.py \
    --concurrent-calls 100 \
    --total-calls 1000 \
    --save-report benchmark_$(date +%Y%m%d).json

# Benchmark API performance
python3 scripts/benchmark_performance.py \
    --duration 300
```

**Store benchmark results for trend analysis:**
```bash
# Create benchmarks directory
mkdir -p benchmarks/$(date +%Y%m)

# Move reports
mv benchmark_*.json benchmarks/$(date +%Y%m)/
```

---

## Scaling Strategies

### Vertical Scaling (Scale Up)

**When to use:**
- Single deployment
- Simple to implement
- Up to ~500 concurrent calls

**Process:**
1. Stop service during maintenance window
2. Increase VM resources (CPU/RAM)
3. Restart service
4. Verify with smoke tests

```bash
# AWS example
aws ec2 modify-instance-attribute \
    --instance-id i-1234567890abcdef0 \
    --instance-type c5.4xlarge
```

### Horizontal Scaling (Scale Out)

**When to use:**
- > 500 concurrent calls
- High availability required
- Geographic distribution

**Architecture:**
```
                    ┌─────────────┐
                    │Load Balancer│
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
    │ PBX #1  │       │ PBX #2  │       │ PBX #3  │
    └────┬────┘       └────┬────┘       └────┬────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │   (Shared)  │
                    └─────────────┘
```

**Process:**
1. Deploy additional PBX instances
2. Configure load balancer
3. Test with gradual traffic shift
4. Monitor for issues

**Load Balancer Configuration:**
- Use DNS SRV for SIP load balancing
- Use HTTP/HTTPS load balancer for API
- Sticky sessions for active calls

### Auto-Scaling

**For Kubernetes:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pbx-autoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pbx
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**For AWS:**
- Use Auto Scaling Groups
- Scale based on CPU/memory metrics
- Use target tracking policies

---

## Monitoring & Alerting

### Key Metrics to Track

**System Metrics:**
```bash
# CPU usage
top -bn1 | grep "Cpu(s)" | awk '{print $2}'

# Memory usage
free -m | awk 'NR==2{printf "%.2f%%\n", $3*100/$2 }'

# Disk usage
df -h / | awk 'NR==2{print $5}'
```

**Application Metrics:**
```bash
# Active calls
curl http://localhost:8080/api/calls | jq 'length'

# Registered extensions
curl http://localhost:8080/api/extensions | jq '[.[] | select(.registered==true)] | length'

# QoS metrics
python3 scripts/diagnose_qos.py
```

### Capacity Alerts

**Configure alerts when:**
- CPU > 80% for 5 minutes
- Memory > 85% for 5 minutes
- Disk > 80% full
- Active calls > 80% of capacity
- Call success rate < 95%
- API response time P95 > 1000ms

---

## Cost Optimization

### Reduce Costs Without Sacrificing Performance

**1. Right-Size Instances**
```bash
# Monitor actual resource usage
python3 scripts/capacity_calculator.py --current-usage
```

**2. Use Reserved Instances** (AWS/Azure)
- Save 30-70% for 1-3 year commitments
- Recommended for production workloads

**3. Optimize Storage**
```bash
# Cleanup old recordings
find recordings/ -mtime +90 -delete

# Cleanup old CDR
python3 scripts/cleanup_cdr.py --days 365
```

**4. Use Spot Instances** (Non-Production)
- Dev/test environments
- Save 50-90% vs on-demand

**5. Database Optimization**
```sql
-- Cleanup old data
DELETE FROM call_detail_records WHERE created_at < NOW() - INTERVAL '1 year';
VACUUM FULL call_detail_records;
```

### Cost Comparison

| Deployment Size | On-Premise (3 years) | AWS (Pay as You Go) | AWS (Reserved) |
|----------------|----------------------|---------------------|----------------|
| Small (100 users) | ~$15,000 | ~$1,440/year | ~$720/year |
| Medium (500 users) | ~$45,000 | ~$9,360/year | ~$4,680/year |
| Large (1000 users) | ~$90,000 | ~$40,080/year | ~$20,040/year |

*Note: On-premise includes server hardware, networking, power, cooling, maintenance*

---

## Appendix

### Capacity Planning Tools

```bash
# Capacity calculator
python3 scripts/capacity_calculator.py

# Load testing
python3 scripts/load_test_sip.py

# Performance benchmarking
python3 scripts/benchmark_performance.py
```

### Related Documentation

- [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) - Operational procedures
- [HA_DEPLOYMENT_GUIDE.md](HA_DEPLOYMENT_GUIDE.md) - High availability setup
- [COMPLETE_GUIDE.md](../COMPLETE_GUIDE.md) - Comprehensive documentation

---
