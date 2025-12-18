# Multi-Site E911 Guide

> **⚠️ DEPRECATED**: This guide has been consolidated into [REGULATIONS_COMPLIANCE_GUIDE.md](REGULATIONS_COMPLIANCE_GUIDE.md#multi-site-e911). Please refer to the "Multi-Site E911" section in the consolidated guide.

**Last Updated**: December 15, 2025  
**Status**: ✅ Production Ready  
**Feature**: Multi-Site Emergency Call Routing

## Overview

The Multi-Site E911 feature provides location-based emergency routing for organizations with multiple physical locations. Each site can have its own emergency trunk, PSAP (Public Safety Answering Point) number, and ELIN (Emergency Location Identification Number), ensuring emergency calls are routed to the correct local emergency services.

### Key Benefits

- **Site-Specific Routing**: Emergency calls automatically routed via the correct trunk for each location
- **Local PSAP Support**: Each site can have a unique PSAP number
- **ELIN Management**: Track Emergency Location Identification Numbers per site
- **IP-Based Detection**: Automatic site detection based on caller IP address
- **Compliance**: Ray Baum's Act and Kari's Law compliant with dispatchable location info
- **High Availability**: Automatic failover to global emergency trunk if site trunk unavailable

## How It Works

### Architecture

```
Caller makes 911 call
    ↓
Kari's Law detects emergency number
    ↓
Get caller's IP address and extension
    ↓
Query Nomadic E911 for location
    ↓
Find site configuration by IP range
    ↓
Route via site-specific emergency trunk
    ↓
Include PSAP and ELIN in routing info
    ↓
Trigger emergency notifications
    ↓
Log emergency call with full details
```

### Emergency Routing Priority

When an emergency call is placed, the system uses this routing priority:

1. **Site-Specific Emergency Trunk** (Highest Priority)
   - Determined by caller's IP address
   - Maps to closest/most appropriate PSAP
   - Includes site-specific ELIN

2. **Global Emergency Trunk** (Fallback)
   - Configured in `config.yml` under `karis_law.emergency_trunk_id`
   - Used if site-specific trunk unavailable

3. **Any Available Trunk** (Last Resort)
   - Standard outbound routing
   - Only used if no emergency trunks available

## Configuration

### Site Configuration

Each site is configured with:

- **Site Name**: Descriptive name (e.g., "Detroit Factory")
- **IP Range**: Start and end IP addresses
- **Emergency Trunk ID**: SIP trunk ID for emergency calls
- **PSAP Number**: Local emergency services number (usually 911)
- **ELIN**: Emergency Location Identification Number (callback number)
- **Full Address**: Street, city, state, postal code, building, floor

### Database Schema

The `multi_site_e911_configs` table stores site configurations:

```sql
CREATE TABLE multi_site_e911_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name TEXT NOT NULL,
    ip_range_start TEXT NOT NULL,
    ip_range_end TEXT NOT NULL,
    emergency_trunk TEXT,
    psap_number TEXT,
    elin TEXT,
    street_address TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'USA',
    building TEXT,
    floor TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### Create Site Configuration

**POST** `/api/framework/nomadic-e911/create-site`

```json
{
  "site_name": "Detroit Factory Building A",
  "ip_range_start": "192.168.10.1",
  "ip_range_end": "192.168.10.255",
  "emergency_trunk": "detroit_e911_trunk",
  "psap_number": "911",
  "elin": "+13135551234",
  "street_address": "123 Factory Lane",
  "city": "Detroit",
  "state": "MI",
  "postal_code": "48201",
  "country": "USA",
  "building": "Building A",
  "floor": ""
}
```

**Response**:
```json
{
  "success": true
}
```

### Get All Sites

**GET** `/api/framework/nomadic-e911/sites`

**Response**:
```json
{
  "sites": [
    {
      "id": 1,
      "site_name": "Detroit Factory Building A",
      "ip_range_start": "192.168.10.1",
      "ip_range_end": "192.168.10.255",
      "emergency_trunk": "detroit_e911_trunk",
      "psap_number": "911",
      "elin": "+13135551234",
      "street_address": "123 Factory Lane",
      "city": "Detroit",
      "state": "MI",
      "postal_code": "48201",
      "country": "USA",
      "building": "Building A",
      "floor": "",
      "created_at": "2025-12-15T10:00:00"
    }
  ]
}
```

### Update Extension Location

**POST** `/api/framework/nomadic-e911/update-location/{extension}`

```json
{
  "ip_address": "192.168.10.50",
  "location_name": "Detroit Factory Building A",
  "street_address": "123 Factory Lane",
  "city": "Detroit",
  "state": "MI",
  "postal_code": "48201",
  "country": "USA",
  "building": "Building A",
  "floor": "1",
  "room": "Assembly Line 3"
}
```

### Auto-Detect Location

**POST** `/api/framework/nomadic-e911/detect-location/{extension}`

```json
{
  "ip_address": "192.168.10.50"
}
```

**Response**:
```json
{
  "ip_address": "192.168.10.50",
  "location_name": "Detroit Factory Building A",
  "street_address": "123 Factory Lane",
  "city": "Detroit",
  "state": "MI",
  "postal_code": "48201",
  "country": "USA",
  "building": "Building A",
  "floor": "",
  "room": "",
  "auto_detected": true
}
```

## Example: Multi-Site Manufacturing Plant

### Scenario

Automotive manufacturing plant with 3 facilities:

1. **Main Factory** (Detroit, MI) - IP Range: 192.168.10.0/24
2. **Warehouse** (Sterling Heights, MI) - IP Range: 192.168.20.0/24
3. **Office Building** (Troy, MI) - IP Range: 192.168.30.0/24

### Configuration Steps

#### 1. Configure SIP Trunks

First, configure emergency SIP trunks for each site in your SIP provider:

```yaml
# config.yml
sip_trunks:
  - trunk_id: detroit_factory_e911
    name: Detroit Factory Emergency
    host: emergency-detroit.provider.com
    port: 5060
    
  - trunk_id: warehouse_e911
    name: Warehouse Emergency
    host: emergency-sterling.provider.com
    port: 5060
    
  - trunk_id: office_e911
    name: Office Emergency
    host: emergency-troy.provider.com
    port: 5060
```

#### 2. Create Site Configurations

**Detroit Factory:**
```bash
curl -X POST http://localhost:8080/api/framework/nomadic-e911/create-site \
  -H "Content-Type: application/json" \
  -d '{
    "site_name": "Detroit Factory",
    "ip_range_start": "192.168.10.1",
    "ip_range_end": "192.168.10.254",
    "emergency_trunk": "detroit_factory_e911",
    "psap_number": "911",
    "elin": "+13135551000",
    "street_address": "1000 Factory Drive",
    "city": "Detroit",
    "state": "MI",
    "postal_code": "48201",
    "building": "Main Factory"
  }'
```

**Warehouse:**
```bash
curl -X POST http://localhost:8080/api/framework/nomadic-e911/create-site \
  -H "Content-Type: application/json" \
  -d '{
    "site_name": "Sterling Heights Warehouse",
    "ip_range_start": "192.168.20.1",
    "ip_range_end": "192.168.20.254",
    "emergency_trunk": "warehouse_e911",
    "psap_number": "911",
    "elin": "+15865552000",
    "street_address": "2000 Warehouse Blvd",
    "city": "Sterling Heights",
    "state": "MI",
    "postal_code": "48310",
    "building": "Warehouse"
  }'
```

**Office:**
```bash
curl -X POST http://localhost:8080/api/framework/nomadic-e911/create-site \
  -H "Content-Type: application/json" \
  -d '{
    "site_name": "Troy Office",
    "ip_range_start": "192.168.30.1",
    "ip_range_end": "192.168.30.254",
    "emergency_trunk": "office_e911",
    "psap_number": "911",
    "elin": "+12485553000",
    "street_address": "3000 Office Plaza",
    "city": "Troy",
    "state": "MI",
    "postal_code": "48084",
    "building": "Corporate Office"
  }'
```

#### 3. Test Emergency Routing

When an extension at IP `192.168.10.50` dials 911:

1. System detects IP is in Detroit Factory range (192.168.10.1-254)
2. Emergency call routed via `detroit_factory_e911` trunk
3. PSAP receives call with ELIN `+13135551000`
4. Dispatchable location: "1000 Factory Drive, Main Factory, Detroit, MI 48201"
5. Local Detroit PSAP receives the call

## Emergency Call Flow

### Example Emergency Call

```
2025-12-15 09:30:15 - PBX - CRITICAL - ======================================================================
2025-12-15 09:30:15 - PBX - CRITICAL - 🚨 EMERGENCY CALL (KARI'S LAW)
2025-12-15 09:30:15 - PBX - CRITICAL - ======================================================================
2025-12-15 09:30:15 - PBX - CRITICAL - Caller Extension: 1001
2025-12-15 09:30:15 - PBX - CRITICAL - Dialed Number: 911
2025-12-15 09:30:15 - PBX - CRITICAL - Call ID: e911-call-12345
2025-12-15 09:30:15 - PBX - INFO - Found site-specific emergency trunk for 1001: detroit_factory_e911
2025-12-15 09:30:15 - PBX - CRITICAL - Routing emergency call via SITE-SPECIFIC trunk: detroit_factory_e911
2025-12-15 09:30:15 - PBX - CRITICAL - Location: 1000 Factory Drive, Main Factory, Detroit, MI 48201
2025-12-15 09:30:15 - PBX - CRITICAL - PSAP: 911
2025-12-15 09:30:15 - PBX - CRITICAL - ELIN: +13135551000
```

### Routing Information

The system returns detailed routing information:

```json
{
  "success": true,
  "trunk_id": "detroit_factory_e911",
  "trunk_name": "Detroit Factory Emergency",
  "destination": "911",
  "site_specific": true,
  "psap_number": "911",
  "elin": "+13135551000",
  "timestamp": "2025-12-15T09:30:15.000Z"
}
```

## Monitoring and Auditing

### Emergency Call History

All emergency calls are logged with:
- Caller extension and name
- Dialed number (911, 9911, etc.) and normalized number
- Call ID and timestamp
- Full location information
- Routing details (trunk, PSAP, ELIN)
- Site information

### Location History

Track location changes for each extension:

**GET** `/api/framework/nomadic-e911/history/{extension}`

```json
{
  "history": [
    {
      "old_location": "Troy Office, 3000 Office Plaza, Troy, MI",
      "new_location": "Detroit Factory, 1000 Factory Drive, Detroit, MI",
      "update_source": "auto",
      "updated_at": "2025-12-15T09:00:00"
    }
  ]
}
```

## Compliance

### Kari's Law

The Multi-Site E911 feature ensures Kari's Law compliance:
- ✅ Direct 911 dialing without prefix
- ✅ Immediate emergency call routing
- ✅ Automatic notification to designated contacts
- ✅ No delay in call routing (site detection is instant)

### Ray Baum's Act

Provides dispatchable location information:
- ✅ Street address
- ✅ Building information
- ✅ Floor and room details
- ✅ City, state, and postal code

### FCC Requirements

Meets FCC multi-line telephone system (MLTS) requirements:
- ✅ Direct 911 access (47 CFR § 9.16)
- ✅ Dispatchable location (47 CFR § 9.23)
- ✅ Notification upon 911 call
- ✅ Location accuracy for multi-site deployments

## Best Practices

### IP Range Planning

1. **Non-Overlapping Ranges**: Ensure IP ranges don't overlap between sites
2. **Document Ranges**: Maintain documentation of all IP ranges
3. **Update Regularly**: Review and update as network changes
4. **Reserve Space**: Leave room for growth in each range

### ELIN Management

1. **Unique per Site**: Each site should have unique ELIN
2. **Test ELINs**: Verify ELINs work with local PSAP
3. **Document**: Maintain ELIN to site mapping
4. **Update Provider**: Ensure SIP provider has correct ELIN info

### Emergency Trunk Configuration

1. **Dedicated Trunks**: Use dedicated trunks for emergency calls
2. **High Capacity**: Ensure sufficient capacity for concurrent emergencies
3. **Test Regularly**: Regular test calls to verify routing
4. **Monitor Health**: Use trunk monitoring to ensure availability

### Testing

1. **Test Mode**: Use test PSAP numbers for testing
2. **Coordinate**: Coordinate with local PSAP for test calls
3. **Document**: Document all test results
4. **Regular Schedule**: Test quarterly or after network changes

## Troubleshooting

### Emergency Call Not Routing to Site-Specific Trunk

**Check**:
1. Extension has location registered with IP address
2. IP address falls within configured site range
3. Site emergency trunk is available and healthy
4. Kari's Law is enabled in configuration

**Debug**:
```bash
# Check location for extension
curl http://localhost:8080/api/framework/nomadic-e911/location/1001

# Check all sites
curl http://localhost:8080/api/framework/nomadic-e911/sites

# Test IP detection
curl -X POST http://localhost:8080/api/framework/nomadic-e911/detect-location/1001 \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "192.168.10.50"}'
```

### Location Not Auto-Detecting

**Causes**:
1. IP address is outside all configured ranges
2. Private IP but no matching site configuration
3. Database connection issue

**Solution**:
1. Verify IP range configuration
2. Check database connectivity
3. Manually update location as temporary fix

### Trunk Failover Not Working

**Check**:
1. Global emergency trunk configured in `config.yml`
2. Fallback trunk is available
3. Review emergency call logs for routing details

## Migration from Single-Site

If upgrading from single-site E911:

1. **Identify Sites**: List all physical locations
2. **Map IP Ranges**: Document IP range for each site
3. **Configure Trunks**: Set up emergency trunk per site
4. **Create Site Configs**: Use API to create site configurations
5. **Test**: Test emergency routing from each site
6. **Update Documentation**: Document new multi-site setup
7. **Keep Global Trunk**: Maintain global trunk as failback

## Related Features

- **Kari's Law**: Direct 911 dialing (pbx/features/karis_law.py)
- **Ray Baum's Act**: Dispatchable location (pbx/features/e911_location.py)
- **Nomadic E911**: Remote worker support (pbx/features/nomadic_e911.py)
- **Emergency Notification**: Auto-alerts on 911 calls
- **SIP Trunking**: Emergency trunk management

## References

- 47 CFR § 9.16 - Kari's Law (Direct 911 Dialing)
- 47 CFR § 9.23 - Ray Baum's Act (Dispatchable Location)
- FCC MLTS Requirements
- NENA i3 Standard (Next Generation 911)

## Support

For issues or questions:
1. Check emergency call logs
2. Verify site and location configurations
3. Test emergency routing with test PSAP
4. Review this guide for troubleshooting steps
