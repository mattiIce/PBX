# Geographic Redundancy Guide

## Overview

The Geographic Redundancy framework enables multi-region SIP trunk registration and automatic failover to ensure high availability and business continuity across geographic locations.

## Features

- **Multi-Region Trunks** - Register SIP trunks in multiple regions
- **Automatic Failover** - Switch to backup region on failure
- **Health Monitoring** - On-demand health checks per region (trunk, network, database, services)
- **Priority-Based Selection** - Configure region priority (lower number = higher priority)
- **Disaster Recovery** - Quick recovery from regional outages

## Use Cases

- **Business Continuity** - Maintain service during regional outages
- **Disaster Recovery** - Quick failover in emergencies
- **Global Operations** - Support distributed workforce
- **Performance** - Route to closest region for lower latency

## Architecture

### Multi-Region Setup

```
┌─────────────────┐
│   Primary PBX   │ (US-East)
│   10.0.1.100    │
└────────┬────────┘
         │
         ├── Region A (US-East)   [ACTIVE]    Priority: 1
         ├── Region B (US-West)   [STANDBY]   Priority: 2
         └── Region C (EU-West)   [STANDBY]   Priority: 3
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

The `GeographicRedundancy` feature reads the following keys from
`features.geographic_redundancy`:

```yaml
features:
  geographic_redundancy:
    enabled: true
    auto_failover: true           # Enable automatic failover (default: true)
    health_check_interval: 60     # Seconds between health checks (default: 60)
    failover_threshold: 3         # Failures before marking a region down (default: 3)
```

Regions and trunks are registered at runtime via the Python API
(`add_region()` / `create_region()`) or the REST API, not through `config.yml`.

## Usage

### Python API

```python
from pbx.features.geographic_redundancy import get_geographic_redundancy, RegionStatus

geo = get_geographic_redundancy()

# Add a region (priority: lower = higher priority)
geo.add_region(
    region_id='us-east-1',
    name='US East',
    location='Virginia, USA',
    priority=1,
    trunks=['trunk-us-east'],
)

# Get active region
active_region = geo.get_active_region()
print(f"Active region: {active_region['name']}")

# Manual failover to a specific region
result = geo.manual_failover('us-west-1')

# Check region health
health = geo.check_region_health('us-east-1')
if health['healthy']:
    print("Region is healthy")

# Get statistics (includes recent failovers)
stats = geo.get_statistics()
```

### REST API Endpoints

#### Create Region
```bash
POST /api/framework/geo-redundancy/region
{
  "region_id": "us-east-1",
  "name": "US East",
  "location": "Virginia, USA"
}
```

#### List All Regions
```bash
GET /api/framework/geo-redundancy/regions

Response:
{
  "regions": [
    {
      "region_id": "us-east-1",
      "name": "US East",
      "location": "Virginia, USA",
      "status": "active",
      "health_score": 1.0,
      "trunk_count": 1,
      "priority": 1,
      "is_active": true
    }
  ]
}
```

#### Get Region Status
```bash
GET /api/framework/geo-redundancy/region/{region_id}
```

#### Trigger Failover (admin only)
```bash
POST /api/framework/geo-redundancy/region/{region_id}/failover
```

#### Get Statistics
```bash
GET /api/framework/geo-redundancy/statistics

Response:
{
  "enabled": true,
  "total_regions": 2,
  "active_region": "us-east-1",
  "total_failovers": 0,
  "recent_failovers": [],
  "auto_failover": true
}
```

## Health Monitoring

Region health is evaluated on demand by `check_region_health(region_id)`. There is
no separate health-check configuration object; the only related config keys are
`health_check_interval` and `failover_threshold` (see [Configuration](#configyml)).

### How Health Is Scored

`check_region_health()` runs four checks and combines them into a single numeric
`health_score` (1.0 = perfect). A region is considered `healthy` when its score is
`>= 0.7`.

| Check | Penalty when failing |
|-------|----------------------|
| Trunks available (at least one trunk can place a call) | -0.4 |
| Network latency `> 100 ms` | -0.2 |
| Database connectivity | -0.3 |
| Critical services running | -0.4 |

```python
health = geo.check_region_health('us-east-1')
# Returns:
# {
#     'healthy': True,                 # bool: health_score >= 0.7
#     'health_score': 1.0,             # float between 0.0 and 1.0
#     'checks': {
#         'trunks_available': True,
#         'network_latency': 12.3,     # milliseconds
#         'database_connected': True,
#         'services_running': True,
#     },
#     'checked_at': '2026-06-19T10:00:00+00:00',
# }
```

When `auto_failover` is enabled and an `ACTIVE` region drops below the healthy
threshold, `check_region_health()` automatically triggers a failover to the
highest-priority healthy backup region.

### Region Status

Each region carries a `RegionStatus` (distinct from the numeric health score):

- **active** - Currently serving traffic
- **standby** - Available as a failover target
- **failed** - Marked down after a failed health check
- **maintenance** - Taken out of rotation

## Admin Panel

Access Geographic Redundancy in the admin panel:

1. Navigate to **Admin Panel** → **Framework Features** → **Geo Redundancy**
2. View region status and health
3. Monitor active region
4. Perform manual failover
5. View failover history

## Best Practices

### Planning
- **Region Selection:** Choose geographically diverse regions
- **Provider Diversity:** Use different SIP providers per region
- **Network Paths:** Ensure independent network connectivity
- **Testing:** Regular failover testing (monthly recommended)

### Configuration
- **Priority Order:** Set clear priority hierarchy (lower number = higher priority)
- **Failover Threshold:** Tune `failover_threshold` so transient blips don't cause false positives

### Operations
- **Monitoring:** Continuously monitor all regions
- **Documentation:** Document failover procedures
- **Runbooks:** Create incident response runbooks
- **Training:** Train staff on manual failover procedures

### Cost Optimization
- **Standby Costs:** Consider costs of standby resources
- **Traffic Routing:** Optimize to minimize cross-region traffic
- **Right-Sizing:** Size each region appropriately

## Database Schema

The geographic redundancy table is created by `pbx/utils/migrations.py`. The
runtime `GeographicRedundancy` feature keeps region state in memory; the table
below stores the persisted per-trunk region configuration.

### trunk_geographic_regions
```sql
CREATE TABLE IF NOT EXISTS trunk_geographic_regions (
    id SERIAL PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,
    trunk_ids TEXT,
    priority INTEGER DEFAULT 100,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Troubleshooting

### Frequent Failovers
**Solution:**
- Increase `failover_threshold` so transient failures don't trigger failover
- Check network stability (latency `> 100 ms` lowers the health score)
- Review trunk capacity

### Failover Not Triggering
**Solution:**
- Verify `auto_failover` is enabled in `config.yml`
- Confirm a healthy, higher-priority backup region exists
- Call `check_region_health()` and inspect the per-check results
- Trigger a manual failover via the REST API to confirm routing works

### Poor Performance After Failover
**Solution:**
- Verify backup region capacity
- Check network latency
- Review codec configuration
- Monitor trunk utilization

## Testing

### Disaster Recovery Drill

```bash
# 1. Trigger a failover away from the primary region (admin only)
POST /api/framework/geo-redundancy/region/us-east-1/failover

# 2. Confirm the active region changed
GET /api/framework/geo-redundancy/statistics

# 3. Verify call routing to backup
GET /api/calls

# 4. Fail back to the primary region when recovered
POST /api/framework/geo-redundancy/region/us-west-1/failover
```

## Next Steps

1. **Plan Regions:** Identify critical geographic regions
2. **Configure Trunks:** Set up SIP trunks in each region
3. **Add Regions:** Register regions and assign trunks/priorities via the Python or REST API
4. **Set Priorities:** Define failover priority order
5. **Test Failover:** Trigger a manual failover and confirm routing
6. **Document Procedures:** Create runbooks
7. **Train Team:** Ensure staff understands procedures
8. **Schedule Drills:** Regular DR testing

## Related Documentation

- [FRAMEWORK_FEATURES_COMPLETE_GUIDE.md](FRAMEWORK_FEATURES_COMPLETE_GUIDE.md)
- [PLANNED_FEATURES.md](../PLANNED_FEATURES.md) - Planned (not-yet-implemented) capabilities for this feature
- [COMPLETE_GUIDE.md](../../COMPLETE_GUIDE.md) - Comprehensive documentation
