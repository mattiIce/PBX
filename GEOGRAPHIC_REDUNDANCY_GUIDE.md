# Geographic Redundancy Guide

## Overview

The Geographic Redundancy framework enables multi-region SIP trunk registration and automatic failover to ensure high availability and business continuity across geographic locations.

## Features

- **Multi-Region Trunks** - Register SIP trunks in multiple regions
- **Automatic Failover** - Switch to backup region on failure
- **Health Monitoring** - Continuous health checks per region
- **Priority-Based Selection** - Configure region priority
- **Data Replication** - Sync critical data across regions
- **Disaster Recovery** - Quick recovery from regional outages

## Use Cases

- **Business Continuity** - Maintain service during regional outages
- **Disaster Recovery** - Quick failover in emergencies
- **Global Operations** - Support distributed workforce
- **Compliance** - Meet regional data residency requirements
- **Performance** - Route to closest region for lower latency

## Architecture

### Multi-Region Setup

```
┌─────────────────┐
│   Primary PBX   │ (US-East)
│   10.0.1.100    │
└────────┬────────┘
         │
         ├── Trunk A (US-East)   [HEALTHY]   Priority: 1
         ├── Trunk B (US-West)   [STANDBY]   Priority: 2
         └── Trunk C (EU-West)   [STANDBY]   Priority: 3
```

### Failover Sequence

```
1. Primary Region Failure Detected
   ↓
2. Health Check Confirms Failure
   ↓
3. Select Next Available Region
   ↓
4. Route Calls to Backup Region
   ↓
5. Monitor Primary for Recovery
   ↓
6. Automatic Failback (Optional)
```

## Configuration

### config.yml
```yaml
features:
  geographic_redundancy:
    enabled: true
    health_check:
      interval: 30              # Health check every 30 seconds
      timeout: 10               # Health check timeout
      retry_count: 3            # Retries before marking down
    failover:
      automatic: true           # Enable automatic failover
      failback: false           # Disable automatic failback
      failback_delay: 300       # Wait 5 minutes before failback
    regions:
      - name: us-east-1
        priority: 1             # Highest priority
        trunk_id: trunk-us-east
        sip_server: sip.us-east.provider.com
        location: "Virginia, USA"
      - name: us-west-1
        priority: 2
        trunk_id: trunk-us-west
        sip_server: sip.us-west.provider.com
        location: "California, USA"
      - name: eu-west-1
        priority: 3
        trunk_id: trunk-eu-west
        sip_server: sip.eu-west.provider.com
        location: "Ireland, EU"
```

## Usage

### Python API

```python
from pbx.features.geographic_redundancy import get_geographic_redundancy, HealthState

geo = get_geographic_redundancy()

# Register a region
geo.register_region(
    name='us-east-1',
    trunk_id='trunk-us-east',
    sip_server='sip.us-east.provider.com',
    priority=1,
    location='Virginia, USA',
    capabilities=['voice', 'sms', 'fax']
)

# Get active region
active_region = geo.get_active_region()
print(f"Active region: {active_region['name']}")

# Manual failover
result = geo.manual_failover(target_region='us-west-1')

# Get region health
health = geo.get_region_health('us-east-1')
if health['state'] == HealthState.HEALTHY:
    print("Region is healthy")

# Get failover history
history = geo.get_failover_history()
```

### REST API Endpoints

#### Register Region
```bash
POST /api/framework/geographic-redundancy/region
{
  "name": "us-east-1",
  "trunk_id": "trunk-us-east",
  "sip_server": "sip.us-east.provider.com",
  "priority": 1,
  "location": "Virginia, USA",
  "capabilities": ["voice", "sms"]
}
```

#### Get Active Region
```bash
GET /api/framework/geographic-redundancy/active-region

Response:
{
  "name": "us-east-1",
  "trunk_id": "trunk-us-east",
  "priority": 1,
  "health_state": "healthy",
  "active_since": "2025-01-15T10:00:00Z"
}
```

#### Manual Failover
```bash
POST /api/framework/geographic-redundancy/failover
{
  "target_region": "us-west-1",
  "reason": "Planned maintenance"
}
```

#### Get Region Status
```bash
GET /api/framework/geographic-redundancy/regions

Response:
{
  "regions": [
    {
      "name": "us-east-1",
      "priority": 1,
      "health_state": "healthy",
      "is_active": true,
      "last_check": "2025-01-15T10:30:00Z"
    },
    {
      "name": "us-west-1",
      "priority": 2,
      "health_state": "healthy",
      "is_active": false,
      "last_check": "2025-01-15T10:30:00Z"
    }
  ]
}
```

#### Get Failover History
```bash
GET /api/framework/geographic-redundancy/failover-history?limit=10

Response:
{
  "failovers": [
    {
      "from_region": "us-east-1",
      "to_region": "us-west-1",
      "reason": "Health check failed",
      "automatic": true,
      "occurred_at": "2025-01-15T09:45:00Z"
    }
  ]
}
```

## Health Monitoring

### Health Check Configuration

```python
# Configure health checks
geo.configure_health_check(
    interval=30,          # Check every 30 seconds
    timeout=10,           # 10 second timeout
    retry_count=3,        # 3 retries before marking down
    check_methods=['sip_options', 'http_ping', 'icmp_ping']
)
```

### Health States

- **HEALTHY** - Region is fully operational
- **WARNING** - Degraded performance detected
- **CRITICAL** - Severe issues, near failure
- **DOWN** - Region is unavailable
- **DEGRADED** - Partial functionality

### Custom Health Checks

```python
# Add custom health check
def custom_health_check(region):
    # Perform custom validation
    try:
        response = requests.get(f'https://{region["sip_server"]}/health')
        return response.status_code == 200
    except:
        return False

geo.add_health_check_method('custom', custom_health_check)
```

## Failover Strategies

### Automatic Failover

```python
# Enable automatic failover
geo.configure_failover(
    automatic=True,
    min_failure_duration=60,  # Fail after 60 seconds of issues
    failover_delay=0          # Immediate failover
)
```

### Planned Failover

```python
# Schedule maintenance window
geo.schedule_failover(
    target_region='us-west-1',
    start_time='2025-01-20T02:00:00Z',
    duration=3600,  # 1 hour
    reason='Planned maintenance'
)
```

### Failback Configuration

```python
# Configure automatic failback
geo.configure_failback(
    enabled=True,
    delay=300,              # Wait 5 minutes after primary recovery
    health_threshold=0.95,  # Require 95% health score
    automatic=False         # Require manual approval
)
```

## Data Replication

### Configuration Data Sync

```python
# Enable configuration replication
geo.enable_data_replication(
    data_types=['extensions', 'voicemail', 'call_queues'],
    sync_interval=60,  # Sync every 60 seconds
    bidirectional=False  # One-way sync from primary
)
```

### CDR Replication

```python
# Replicate call detail records
geo.replicate_cdr(
    target_regions=['us-west-1', 'eu-west-1'],
    realtime=True
)
```

## Load Balancing

### Geographic Load Balancing

```python
# Distribute calls based on caller location
geo.enable_geo_load_balancing(
    strategy='proximity',  # Route to nearest region
    weights={
        'us-east-1': 50,   # 50% of traffic
        'us-west-1': 30,   # 30% of traffic
        'eu-west-1': 20    # 20% of traffic
    }
)
```

### Time-Based Routing

```python
# Route based on time of day (follow the sun)
geo.configure_time_based_routing({
    '00:00-08:00': 'eu-west-1',   # Night in US, use EU
    '08:00-17:00': 'us-east-1',   # Business hours, use primary
    '17:00-24:00': 'us-west-1'    # Evening, use west coast
})
```

## Monitoring & Alerts

### Failover Alerts

```python
# Configure alerts
geo.configure_alerts(
    email=['ops@company.com'],
    sms=['+1555123456'],
    webhook='https://hooks.company.com/geo-redundancy',
    on_events=['failover', 'region_down', 'region_degraded']
)
```

### Metrics Collection

```python
# Get region metrics
metrics = geo.get_region_metrics('us-east-1')
# Returns:
# {
#     'uptime_percentage': 99.95,
#     'average_latency_ms': 45,
#     'calls_handled': 12345,
#     'failover_count': 2,
#     'last_failover': '2025-01-10T15:30:00Z'
# }
```

## Admin Panel

Access Geographic Redundancy in the admin panel:

1. Navigate to **Admin Panel** → **Framework Features** → **Geo Redundancy**
2. View region status and health
3. Monitor active region
4. Perform manual failover
5. View failover history
6. Configure health checks
7. Set up alerts

## Best Practices

### Planning
- **Region Selection:** Choose geographically diverse regions
- **Provider Diversity:** Use different SIP providers per region
- **Network Paths:** Ensure independent network connectivity
- **Testing:** Regular failover testing (monthly recommended)

### Configuration
- **Priority Order:** Set clear priority hierarchy
- **Health Thresholds:** Don't set too sensitive to avoid false positives
- **Failback Delay:** Allow time for stability before failing back
- **Alerting:** Configure comprehensive alerting

### Operations
- **Monitoring:** Continuously monitor all regions
- **Documentation:** Document failover procedures
- **Runbooks:** Create incident response runbooks
- **Training:** Train staff on manual failover procedures

### Cost Optimization
- **Standby Costs:** Consider costs of standby resources
- **Traffic Routing:** Optimize to minimize cross-region traffic
- **Data Transfer:** Minimize unnecessary data replication
- **Right-Sizing:** Size each region appropriately

## Database Schema

### geo_regions
```sql
CREATE TABLE geo_regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    trunk_id VARCHAR(100) NOT NULL,
    sip_server VARCHAR(255) NOT NULL,
    priority INTEGER NOT NULL,
    location VARCHAR(100),
    capabilities TEXT[],
    health_state VARCHAR(20),
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_priority (priority),
    INDEX idx_health_state (health_state)
);
```

### geo_failover_history
```sql
CREATE TABLE geo_failover_history (
    id SERIAL PRIMARY KEY,
    from_region VARCHAR(50),
    to_region VARCHAR(50) NOT NULL,
    reason TEXT,
    automatic BOOLEAN DEFAULT true,
    initiated_by VARCHAR(100),
    duration_ms INTEGER,
    occurred_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_occurred_at (occurred_at)
);
```

### geo_health_checks
```sql
CREATE TABLE geo_health_checks (
    id SERIAL PRIMARY KEY,
    region_name VARCHAR(50) NOT NULL,
    check_method VARCHAR(50) NOT NULL,
    success BOOLEAN NOT NULL,
    latency_ms INTEGER,
    error_message TEXT,
    checked_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_region_checked (region_name, checked_at)
);
```

## Troubleshooting

### Frequent Failovers
**Solution:**
- Increase health check timeout
- Reduce health check sensitivity
- Check network stability
- Review trunk capacity

### Failover Not Triggering
**Solution:**
- Verify automatic failover is enabled
- Check health check configuration
- Review retry count settings
- Test manual failover

### Poor Performance After Failover
**Solution:**
- Verify backup region capacity
- Check network latency
- Review codec configuration
- Monitor trunk utilization

### Failed Failback
**Solution:**
- Verify primary region is fully recovered
- Check failback delay settings
- Review health threshold requirements
- Test primary region manually

## Testing

### Failover Testing

```python
# Perform failover test
test_result = geo.test_failover(
    from_region='us-east-1',
    to_region='us-west-1',
    dry_run=True  # Don't actually failover
)

print(f"Test result: {test_result}")
```

### Disaster Recovery Drill

```bash
# 1. Simulate region failure
POST /api/framework/geographic-redundancy/simulate-failure
{
  "region": "us-east-1",
  "duration": 300  # 5 minutes
}

# 2. Observe automatic failover
GET /api/framework/geographic-redundancy/active-region

# 3. Verify call routing to backup
GET /api/calls

# 4. End simulation
POST /api/framework/geographic-redundancy/end-simulation
```

## Compliance & Regulations

### Data Residency
Some regions have data residency requirements:

```python
# Configure data residency constraints
geo.configure_data_residency(
    'eu-west-1',
    constraints={
        'data_types': ['cdr', 'recordings', 'personal_data'],
        'storage_location': 'eu-west-1',
        'no_transfer_outside_eu': True
    }
)
```

### GDPR Compliance
For EU regions:

```python
# Enable GDPR compliance mode
geo.enable_gdpr_compliance(
    region='eu-west-1',
    data_processing_agreement=True,
    user_consent_required=True
)
```

## Next Steps

1. **Plan Regions:** Identify critical geographic regions
2. **Configure Trunks:** Set up SIP trunks in each region
3. **Set Priorities:** Define failover priority order
4. **Enable Monitoring:** Configure health checks
5. **Test Failover:** Perform failover testing
6. **Document Procedures:** Create runbooks
7. **Train Team:** Ensure staff understands procedures
8. **Schedule Drills:** Regular DR testing

## See Also

- [FRAMEWORK_FEATURES_COMPLETE_GUIDE.md](FRAMEWORK_FEATURES_COMPLETE_GUIDE.md)
- [SIP_TRUNK_GUIDE.md](SIP_TRUNK_GUIDE.md)
- [DNS_SRV_FAILOVER_GUIDE.md](DNS_SRV_FAILOVER_GUIDE.md)
- [MULTI_SITE_E911_GUIDE.md](MULTI_SITE_E911_GUIDE.md)
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
